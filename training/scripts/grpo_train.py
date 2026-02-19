#!/usr/bin/env python3
"""
Group Relative Policy Optimization (GRPO) Training Script for PantryPilot

Reinforcement learning stage that optimizes tool-calling behavior using
reward signals from ToolCallRewardComputer. Starts from an SFT checkpoint
and further aligns the model for correct tool selection, argument
completeness, and search query expansion.

Pipeline position: DAPT → SFT → **GRPO**

Usage:
    # From SFT checkpoint (default workflow)
    python grpo_train.py --base_model ./outputs/sft \
                         --prompts_path ../data/grpo_prompts.json \
                         --output_dir ./outputs/grpo

    # From HuggingFace model (skip SFT)
    python grpo_train.py --base_model unsloth/Qwen2.5-0.5B-Instruct-bnb-4bit \
                         --prompts_path ../data/grpo_prompts.json \
                         --output_dir ./outputs/grpo

    # With custom reward weights
    python grpo_train.py --base_model ./outputs/sft \
                         --prompts_path ../data/grpo_prompts.json \
                         --json_weight 1.0 --tool_weight 3.0 \
                         --args_weight 1.5 --query_weight 1.0

    # Granite 4.0 Mamba2 (install CUDA kernels)
    python grpo_train.py --base_model ./outputs/sft \
                         --prompts_path ../data/grpo_prompts.json \
                         --install_mamba
"""

import argparse
import json
import os
import subprocess
import sys

# Disable Unsloth's padding-free auto-enable BEFORE importing unsloth.
# V100 GPUs lack Flash Attention 2, and Unsloth's padding-free mode
# causes SDPA tensor size mismatches on the FA2-less fallback path.
os.environ["UNSLOTH_DISABLE_AUTO_PADDING_FREE"] = "1"

# Disable torch.compile BEFORE importing unsloth/trl/torch.
# Unsloth compiles its GRPO trainer cache at import time — setting
# TORCHDYNAMO_DISABLE after imports has no effect on already-compiled
# functions like chunked_hidden_states_selective_log_softmax.
# LFM2 hybrid models produce hidden states whose symbolic shapes
# can't be resolved by dynamo's FX tracer, causing matmul dim errors.
if "--disable_dynamo" in sys.argv:
    os.environ["TORCHDYNAMO_DISABLE"] = "1"
    print("⚠️ torch.compile disabled (--disable_dynamo) — using eager execution")

import mlflow
import torch

# Unsloth MUST be imported before trl, transformers, peft
# to ensure all optimisation patches are applied.
import unsloth  # noqa: F401  (side-effect import for patching)
from datasets import Dataset
from reward_functions import ToolCallRewardComputer
from trl import GRPOConfig, GRPOTrainer
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template

# ---------------------------------------------------------------------------
# Condensed system prompt for GRPO rollouts.
#
# During SFT the model sees the full ~10K-char Nibble system prompt which
# describes tool *usage rules* in natural language.  During GRPO rollouts
# the model must also know:
#   1. Its identity (Nibble, meal planning assistant)
#   2. The exact set of available tools with parameter schemas
#   3. How to format tool calls (<tool_call> JSON)
#   4. When NOT to call tools (general chat, out-of-scope)
#
# We keep this condensed (~2K chars) to fit within context alongside the
# generated completions.  The reward function handles scoring; the system
# prompt just gives the model enough context to produce well-formed calls.
# ---------------------------------------------------------------------------

GRPO_SYSTEM_PROMPT = """\
You are Nibble, a friendly meal planning assistant for families.

You have access to the following tools. When a user request requires a tool,
respond with a single tool call using this exact format:
<tool_call>
{"name": "<tool_name>", "arguments": {<args>}}
</tool_call>

If the user's message does NOT require a tool (greetings, general cooking
knowledge, thanks, or off-topic requests), respond with helpful text only.
For off-topic requests, politely redirect to food/cooking topics.

Available tools:

1. search_recipes - Search the user's recipe collection
   Parameters:
   - query (string, optional): Search text
   - cuisine (string, optional): Filter by cuisine
   - difficulty (string, optional): "easy", "medium", or "hard"
   - max_cook_time (integer, optional): Maximum cook time in minutes
   - sort_by (string, optional): Sort field e.g. "times_cooked"
   - include_full_recipe (boolean, optional): Return full recipe details

2. get_recipe_details - Get full ingredients/instructions for one recipe
    Parameters:
    - recipe_id (string, required): Recipe UUID from search_recipes results

3. get_meal_plan_history - View past meal plans
   Parameters:
   - days (integer, optional): Number of days to look back (default 14)

4. suggest_recipe - Save a new recipe to the collection
   Parameters (all required):
   - title (string): Recipe name
   - description (string): Brief description
   - prep_time_minutes (integer): Preparation time
   - cook_time_minutes (integer): Cooking time
   - serving_min (integer): Minimum servings
   - instructions (string): Step-by-step instructions
   - category (string): Recipe category
   - ingredients (array): List of ingredients
   Optional:
   - source_url (string): Original recipe URL

5. update_user_memory - Remember user preferences and dietary info
   Parameters:
   - memory_content (string, required): Updated memory content in markdown

6. propose_meal_for_day - Propose a meal for a specific date
   Parameters:
   - date (string, required): ISO date e.g. "2026-01-25"
   - day_label (string, required): e.g. "Saturday"
   Plus optional fields for existing/new recipes, leftovers, eating out

7. get_daily_weather - Get weather for meal planning context
   No parameters required.

8. web_search - Search the web for recipe ideas
   Parameters:
   - query (string, required): Search query

9. fetch_url_as_markdown - Fetch a webpage as markdown text
   Parameters:
   - url (string, required): URL to fetch
"""


# ---------------------------------------------------------------------------
# Patch for chunked_hidden_states_selective_log_softmax (LFM2 compat)
#
# Unsloth's GRPO path uses chunked_hidden_states_selective_log_softmax:
#   1. Run model with output_hidden_states=True
#   2. Extract last hidden state  (batch, seq, hidden_size)
#   3. Manually compute  hidden_states @ lm_head.T  per chunk
#
# LFM2 hybrid (transformer + SSM) models break step 2 — Unsloth
# extracts a tensor with shape (batch, seq, vocab_size) instead of
# (batch, seq, hidden_size), causing a matmul dimension mismatch.
#
# The official LFM2.5 GRPO Colab notebook avoids this by using vLLM
# sampling params, which takes an entirely different generation path.
# Our V100 environment doesn't have vLLM, so we hit this code path.
#
# Fix: monkey-patch the function in the compiled cache module AFTER
# imports but BEFORE training to detect the shape mismatch and skip
# the redundant matmul when hidden_states are already logits.
# ---------------------------------------------------------------------------


def _patch_chunked_log_softmax_for_lfm2():
    """Patch chunked_hidden_states_selective_log_softmax in Unsloth's
    compiled GRPO trainer cache to handle LFM2 hidden state shapes.

    LFM2 outputs hidden states with vocab_size dim (already logits)
    instead of hidden_size dim. We detect this and skip the matmul.
    """
    import sys

    # Find the compiled cache module
    cache_mod = None
    for name, mod in sys.modules.items():
        if "UnslothGRPOTrainer" in name and hasattr(
            mod, "chunked_hidden_states_selective_log_softmax"
        ):
            cache_mod = mod
            break

    if cache_mod is None:
        print(
            "⚠️ Could not find UnslothGRPOTrainer compiled cache module, "
            "skipping LFM2 log-softmax patch"
        )
        return

    original_fn = cache_mod.chunked_hidden_states_selective_log_softmax

    def patched_chunked_hidden_states_selective_log_softmax(*args, **kwargs):
        """Wrapper that detects LFM2 shape mismatch and uses standard
        log_softmax instead of manual matmul when hidden_states are
        already in vocab_size space.
        """
        import torch

        # Extract hidden_states and lm_head from positional args.
        # Signature: (hidden_states, lm_head, token_ids, ...)
        if len(args) >= 2:
            hidden_states = args[0]
            lm_head = args[1]

            # Check for LFM2 case: hidden_states last dim == vocab_size
            # (should be hidden_size for normal models)
            if hidden_states.shape[-1] == lm_head.shape[0]:
                # hidden_states is already logits — skip the matmul.
                # Replace hidden_states with a version Unsloth can use:
                # Project logits back to hidden_size via lm_head pseudoinverse
                # is too expensive. Instead, use logits directly.
                #
                # Compute per-token log_softmax manually:
                token_ids = args[2]

                # Apply temperature if in kwargs or args
                temperature = kwargs.get("temperature", None)
                if temperature is None and len(args) >= 5:
                    temperature = args[4]
                if temperature is None:
                    temperature = 1.0

                logits = hidden_states.float()
                # Numerical safety for hybrid-model patched path on fp16 GPUs.
                logits = torch.nan_to_num(
                    logits,
                    nan=0.0,
                    posinf=1e4,
                    neginf=-1e4,
                )
                logits = torch.clamp(logits, min=-80.0, max=80.0)
                if temperature != 1.0:
                    logits = logits / temperature

                log_probs = torch.log_softmax(logits, dim=-1)

                # Gather per-token log probs for arbitrary token_ids shapes.
                # token_ids may be [N] or [B, T] depending on TRL/Unsloth path,
                # so use torch.gather on the vocab dimension.
                token_ids = token_ids.to(device=log_probs.device, dtype=torch.long)

                # Preferred path: token_ids shape matches logits prefix dims.
                if token_ids.ndim == log_probs.ndim - 1:
                    gathered = torch.gather(
                        log_probs,
                        dim=-1,
                        index=token_ids.unsqueeze(-1),
                    ).squeeze(-1)
                    return torch.nan_to_num(
                        gathered,
                        nan=-30.0,
                        posinf=0.0,
                        neginf=-80.0,
                    )

                # Fallback path: flatten any extra structure and restore shape.
                vocab_size = log_probs.shape[-1]
                flat_log_probs = log_probs.reshape(-1, vocab_size)
                flat_token_ids = token_ids.reshape(-1)
                selected = torch.gather(
                    flat_log_probs,
                    dim=-1,
                    index=flat_token_ids.unsqueeze(-1),
                ).squeeze(-1)

                selected = torch.nan_to_num(
                    selected,
                    nan=-30.0,
                    posinf=0.0,
                    neginf=-80.0,
                )

                if token_ids.numel() == selected.numel():
                    return selected.reshape(token_ids.shape)
                return selected

        # Standard path — hidden_states shape matches, use original
        return original_fn(*args, **kwargs)

    # Replace in the module namespace so all callers see the patch
    cache_mod.chunked_hidden_states_selective_log_softmax = (
        patched_chunked_hidden_states_selective_log_softmax
    )
    print(
        "✅ Patched chunked_hidden_states_selective_log_softmax "
        "for LFM2 hidden-state shape compatibility"
    )


def install_mamba_kernels() -> None:
    """Install mamba_ssm and causal_conv1d CUDA kernels at runtime.

    These packages require ``--no-build-isolation`` so they can compile
    against the already-installed PyTorch/CUDA.  That flag is not
    supported in conda environment YAML pip sections, so we install
    them here instead — only when the ``--install_mamba`` flag is set.
    """
    packages = [
        ("mamba_ssm", "2.2.5"),
        ("causal_conv1d", "1.5.2"),
    ]
    for pkg, ver in packages:
        print(f"📦 Installing {pkg}=={ver} (--no-build-isolation)...")
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-build-isolation",
                f"{pkg}=={ver}",
            ],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    print("✅ Mamba CUDA kernels installed")


def load_prompts(prompts_path: str, tokenizer) -> tuple[Dataset, list[dict]]:
    """Load GRPO prompts and format as chat-template conversations.

    Each prompt is wrapped in a chat message list with the Nibble system
    prompt (including tool schemas) so the model knows what tools are
    available and how to format calls — matching the SFT training
    distribution.

    The ``prompt`` column contains the tokenizer-rendered string (ChatML)
    so GRPOTrainer can tokenize it directly.

    Args:
        prompts_path: Path to grpo_prompts.json or Azure ML Data Asset name
        tokenizer: HuggingFace tokenizer with chat template applied

    Returns:
        Tuple of (HuggingFace Dataset, raw prompt dicts)
    """
    if prompts_path.startswith("pantrypilot-"):
        # Load from Azure ML Data Asset
        from azure.ai.ml import MLClient
        from azure.identity import DefaultAzureCredential

        ml_client = MLClient.from_config(DefaultAzureCredential())
        if ":" in prompts_path:
            asset_name, version = prompts_path.split(":")
        else:
            asset_name = prompts_path
            version = None
        data_asset = ml_client.data.get(name=asset_name, version=version)
        prompts_path = data_asset.path

    with open(prompts_path) as f:
        raw_prompts = json.load(f)

    print(f"📚 Loaded {len(raw_prompts)} prompts from {prompts_path}")

    # Format each prompt as a chat conversation with system context.
    # GRPOTrainer accepts pre-rendered prompt strings; we apply the chat
    # template here so the model sees the same ChatML format as during SFT.
    prompts = []
    for item in raw_prompts:
        messages = [
            {"role": "system", "content": GRPO_SYSTEM_PROMPT},
            {"role": "user", "content": item["prompt"]},
        ]
        rendered = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        prompts.append(
            {
                "prompt": rendered,
                "expected_tool": item.get("expected_tool"),
                "category": item.get("category", "unknown"),
                # Keep raw user text for reward function lookups
                "raw_prompt": item["prompt"],
                # JSON-serialised keyword list for reward scoring
                "expected_query_keywords": json.dumps(
                    item.get("expected_query_keywords", [])
                ),
            }
        )

    return Dataset.from_list(prompts), raw_prompts


def build_reward_fn(
    raw_prompts: list[dict],
    reward_computer: ToolCallRewardComputer,
) -> callable:
    """Build reward function that maps prompts to expected tools.

    Creates a lookup from prompt text → expected tool so the reward
    function can score completions correctly during GRPO training.
    """
    prompt_to_expected: dict[str, str | None] = {}
    for item in raw_prompts:
        prompt_to_expected[item["prompt"]] = item.get("expected_tool")

    def reward_fn(
        completions,
        prompts=None,
        expected_tool=None,
        raw_prompt=None,
        expected_query_keywords=None,
        **kwargs,
    ) -> list[float]:
        """Compute rewards for a batch of completions.

        TRL GRPOTrainer calls reward functions with keyword arguments:
        prompts, completions, completion_ids, trainer_state, plus any
        extra dataset columns (expected_tool, category, raw_prompt,
        expected_query_keywords, etc.).

        ``prompts`` contains the full chat-template-rendered text.
        ``raw_prompt`` contains the original user text (used for lookups).
        ``expected_query_keywords`` contains JSON-serialised keyword lists
        for per-prompt objective query scoring.
        """
        rewards = []
        for i, completion in enumerate(completions):
            # Use raw_prompt (original user text) for reward context
            user_text = (
                raw_prompt[i]
                if raw_prompt is not None
                else (prompts[i] if prompts else "")
            )
            # Use dataset column if available, fall back to lookup dict
            if expected_tool is not None:
                exp_tool = expected_tool[i]
            else:
                exp_tool = prompt_to_expected.get(user_text)
            # Parse expected keywords from JSON string column
            keywords = None
            if expected_query_keywords is not None:
                try:
                    keywords = json.loads(expected_query_keywords[i])
                except (json.JSONDecodeError, TypeError, IndexError):
                    keywords = None
            score = reward_computer.compute_total_reward(
                completion=completion,
                prompt=user_text,
                expected_tool=exp_tool,
                expected_query_keywords=keywords,
            )
            rewards.append(score)
        return rewards

    return reward_fn


def _resolve_vllm_attention_backend(backend_arg: str) -> str | None:
    """Resolve the vLLM attention backend env var value.

    Returns backend token for ``VLLM_ATTENTION_BACKEND`` or ``None``
    to keep vLLM defaults.

    Auto mode forces XFORMERS on pre-Ampere GPUs (< 8.0 capability),
    because FlashInfer requires newer compute capability.
    """
    mapping = {
        "flashinfer": "FLASHINFER",
        "xformers": "XFORMERS",
        "flashattn": "FLASH_ATTN",
        "sdpa": "TORCH_SDPA",
    }

    if backend_arg != "auto":
        return mapping[backend_arg]

    if not torch.cuda.is_available():
        return None

    major, minor = torch.cuda.get_device_capability(0)
    if major < 8:
        print(
            "⚠️ Detected pre-Ampere GPU "
            f"(compute capability {major}.{minor}) — "
            "forcing vLLM attention backend to XFORMERS"
        )
        return "XFORMERS"

    return None


def main(args: argparse.Namespace) -> None:
    """Main GRPO training function."""
    # Start MLflow run
    mlflow.start_run(run_name=args.run_name)

    # vLLM support (preferred path for LFM2 hybrid architectures)
    vllm_available = False
    SamplingParams = None
    if args.use_vllm:
        selected_backend = _resolve_vllm_attention_backend(args.vllm_attention_backend)
        if selected_backend:
            os.environ["VLLM_ATTENTION_BACKEND"] = selected_backend
            print(f"✅ Set VLLM_ATTENTION_BACKEND={selected_backend}")

        try:
            from vllm import SamplingParams as _SamplingParams

            SamplingParams = _SamplingParams
            vllm_available = True
            # Match Unsloth's official notebooks; keeps a vLLM worker warm.
            os.environ.setdefault("UNSLOTH_VLLM_STANDBY", "1")
        except ImportError:
            print(
                "⚠️ --use_vllm set but vLLM is not installed in this environment. "
                "Falling back to native generation."
            )

    print(f"🚀 Starting GRPO training with {args.base_model}")
    print(f"📊 Max sequence length: {args.max_seq_length}")
    print(f"🔧 LoRA rank: {args.lora_r}, alpha: {args.lora_alpha}")
    print(
        f"🎯 Reward weights: json={args.json_weight}, tool={args.tool_weight}, "
        f"args={args.args_weight}, query={args.query_weight}"
    )

    # Load model from SFT checkpoint or HuggingFace
    load_4bit = not args.no_4bit
    print(f"\n📦 Loading model (4-bit={load_4bit})...")

    from_pretrained_kwargs = {
        "model_name": args.base_model,
        "max_seq_length": args.max_seq_length,
        "load_in_4bit": load_4bit,
        "dtype": None,  # Auto-detect
        "device_map": "auto",
        "max_lora_rank": args.lora_r,  # Pre-allocate LoRA dims for LFM2 dynamo compat
    }

    # vLLM engine is created only when fast_inference=True.
    # Unsloth's GRPOTrainer expects model.vllm_engine when --use_vllm.
    requested_vllm = args.use_vllm and vllm_available
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            fast_inference=requested_vllm,
            **from_pretrained_kwargs,
        )
    except RuntimeError as exc:
        error_text = str(exc)
        vllm_lora_error = "BaseLayerWithLoRA" in error_text
        if requested_vllm and vllm_lora_error:
            print(
                "⚠️ vLLM LoRA initialisation failed for this model "
                "(unsupported non-LoRA layer registration). "
                "Retrying with native generation (--use_vllm fallback)."
            )
            vllm_available = False
            model, tokenizer = FastLanguageModel.from_pretrained(
                fast_inference=False,
                **from_pretrained_kwargs,
            )
        else:
            raise

    # Apply ChatML chat template so apply_chat_template() works in
    # load_prompts() and GRPOTrainer rollout tokenisation.
    tokenizer = get_chat_template(tokenizer, chat_template="chatml")
    print("✅ Applied ChatML chat template to tokenizer")

    # Apply LoRA with higher rank for RL (default 32 vs SFT's 16)
    if args.target_modules:
        target_modules = args.target_modules.split(",")
    else:
        target_modules = [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    print(
        f"\n🔧 Applying LoRA adapters (r={args.lora_r}, "
        f"target_modules={target_modules})..."
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0,
        target_modules=target_modules,
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    # Load prompts
    print("\n📚 Loading GRPO prompts...")
    prompt_dataset, raw_prompts = load_prompts(args.prompts_path, tokenizer)
    print(f"✅ {len(prompt_dataset)} prompts loaded")

    # Category breakdown
    categories: dict[str, int] = {}
    for item in raw_prompts:
        cat = item.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in sorted(categories.items()):
        print(f"   {cat}: {count} prompts")

    # Initialize reward computer with configurable weights
    reward_computer = ToolCallRewardComputer(
        json_weight=args.json_weight,
        tool_weight=args.tool_weight,
        args_weight=args.args_weight,
        query_weight=args.query_weight,
    )

    # Build reward function with expected-tool lookup
    reward_fn = build_reward_fn(raw_prompts, reward_computer)

    # Log hyperparameters manually (Azure ML 200-param limit)
    mlflow.log_params(
        {
            "base_model": args.base_model,
            "max_seq_length": args.max_seq_length,
            "batch_size": args.batch_size,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
            "learning_rate": args.learning_rate,
            "num_epochs": args.num_epochs,
            "lora_r": args.lora_r,
            "lora_alpha": args.lora_alpha,
            "target_modules": ",".join(target_modules),
            "load_in_4bit": load_4bit,
            "num_generations": args.num_generations,
            "temperature": args.temperature,
            "beta": args.beta,
            "max_new_tokens": args.max_new_tokens,
            "json_weight": args.json_weight,
            "tool_weight": args.tool_weight,
            "args_weight": args.args_weight,
            "query_weight": args.query_weight,
            "seed": args.seed,
        }
    )
    mlflow.set_tags(
        {
            "num_prompts": str(len(prompt_dataset)),
            "categories": json.dumps(categories),
            "stage": "grpo",
        }
    )

    # GRPO training configuration
    print("\n⚙️ Setting up GRPO training configuration...")
    grpo_kwargs: dict = dict(
        output_dir=args.output_dir,
        report_to="none",  # Disable built-in MLflow (Azure ML 200-param limit)
        run_name=args.run_name,
        num_generations=args.num_generations,
        temperature=args.temperature,
        max_completion_length=args.max_new_tokens,  # was max_new_tokens in older TRL
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        lr_scheduler_type="constant",
        warmup_ratio=0.0,
        beta=args.beta,
        num_train_epochs=args.num_epochs,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=3,
        max_grad_norm=1.0,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        seed=args.seed,
    )

    # Use vLLM for generation when available — this takes a completely
    # different code path that avoids Unsloth's
    # chunked_hidden_states_selective_log_softmax (which breaks on LFM2
    # hybrid architectures). Matches the official LFM2.5 GRPO Colab.
    if args.use_vllm and vllm_available:
        grpo_kwargs["use_vllm"] = True
        grpo_kwargs["vllm_sampling_params"] = SamplingParams(
            min_tokens=64,
            max_tokens=args.max_new_tokens,
            stop=["<|im_end|>"],
            include_stop_str_in_output=True,
        )
        print("✅ vLLM generation enabled (official hybrid-model path)")

    training_args = GRPOConfig(**grpo_kwargs)

    # Patch chunked_hidden_states_selective_log_softmax for LFM2 compat
    # BEFORE creating the trainer (the compiled cache module may be loaded
    # at trainer init time).
    if args.patch_lfm2_logps:
        _patch_chunked_log_softmax_for_lfm2()

    # Initialize GRPO trainer
    print("\n🏋️ Initializing GRPOTrainer...")
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        args=training_args,
        train_dataset=prompt_dataset,
        reward_funcs=[reward_fn],
    )

    # If the compiled cache was loaded lazily, try patching again
    if args.patch_lfm2_logps:
        _patch_chunked_log_softmax_for_lfm2()

    # Train
    print("\n🔥 Starting GRPO training...")
    trainer.train()

    # Save final model
    print("\n💾 Saving final model...")
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    # Save LoRA adapters separately
    lora_output_dir = os.path.join(args.output_dir, "lora_adapters")
    print(f"💾 Saving LoRA adapters to {lora_output_dir}...")
    model.save_pretrained(lora_output_dir)

    # Azure ML automatically uploads everything under ./outputs/

    # Export GGUF if requested
    if args.export_gguf:
        print("\n🔧 Exporting GGUF model...")
        gguf_output_dir = os.path.join(args.output_dir, "gguf")
        os.makedirs(gguf_output_dir, exist_ok=True)
        model.save_pretrained_gguf(
            gguf_output_dir, tokenizer, quantization_method=args.gguf_quantization
        )
        print(f"✅ GGUF model exported to {gguf_output_dir}")

    # Log final metrics
    run_id = mlflow.active_run().info.run_id
    mlflow.end_run()

    print("\n✅ GRPO training complete!")
    print(f"📁 Model saved to: {args.output_dir}")
    print(f"📊 MLflow run: {run_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train PantryPilot GRPO model with Unsloth + TRL"
    )

    # Model arguments
    parser.add_argument(
        "--base_model",
        type=str,
        default="./outputs/sft",
        help="SFT checkpoint path or HuggingFace model ID (default: ./outputs/sft)",
    )
    parser.add_argument(
        "--max_seq_length",
        type=int,
        default=4096,
        help="Maximum sequence length (supports 4096, 8192, 16384 via RoPE scaling)",
    )

    # Data arguments
    parser.add_argument(
        "--prompts_path",
        type=str,
        required=True,
        help="Path to grpo_prompts.json or Azure ML Data Asset name",
    )

    # Output arguments
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./outputs/grpo",
        help="Output directory for model checkpoints",
    )
    parser.add_argument(
        "--run_name",
        type=str,
        default="grpo-run",
        help="MLflow run name",
    )

    # GRPO-specific hyperparameters
    parser.add_argument(
        "--num_generations",
        type=int,
        default=8,
        help="Number of completions per prompt for group comparison. "
        "Higher values (8-16) provide more reward variance for GRPO learning.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="Sampling temperature for generation. "
        "Higher values (0.9-1.2) encourage exploration and reward diversity.",
    )
    parser.add_argument(
        "--max_new_tokens",
        type=int,
        default=512,
        help="Maximum tokens generated per completion",
    )
    parser.add_argument(
        "--beta",
        type=float,
        default=0.01,
        help="KL divergence penalty coefficient",
    )

    # Training hyperparameters
    parser.add_argument(
        "--batch_size",
        type=int,
        default=1,
        help="Per-device batch size (keep low for GRPO "
        "— each prompt expands to num_generations)",
    )
    parser.add_argument(
        "--gradient_accumulation_steps",
        type=int,
        default=4,
        help="Gradient accumulation steps",
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=5e-6,
        help="Peak learning rate (lower than SFT default)",
    )
    parser.add_argument(
        "--num_epochs",
        type=int,
        default=2,
        help="Number of training epochs. "
        "2-3 recommended for GRPO to accumulate gradient signal.",
    )

    # LoRA configuration (higher rank for RL)
    parser.add_argument(
        "--lora_r",
        type=int,
        default=32,
        help="LoRA rank — higher than SFT (16) for RL exploration",
    )
    parser.add_argument(
        "--lora_alpha",
        type=int,
        default=32,
        help="LoRA alpha",
    )
    parser.add_argument(
        "--target_modules",
        type=str,
        default=None,
        help="Comma-separated LoRA target modules "
        "(default: q/k/v/o/gate/up/down_proj). "
        "For LFM2.5: q_proj,k_proj,v_proj,out_proj,in_proj,w1,w2,w3",
    )

    # Reward function weights
    parser.add_argument(
        "--json_weight",
        type=float,
        default=1.0,
        help="Reward weight for JSON validity",
    )
    parser.add_argument(
        "--tool_weight",
        type=float,
        default=2.0,
        help="Reward weight for correct tool selection",
    )
    parser.add_argument(
        "--args_weight",
        type=float,
        default=1.5,
        help="Reward weight for argument completeness",
    )
    parser.add_argument(
        "--query_weight",
        type=float,
        default=1.0,
        help="Reward weight for search query expansion quality",
    )

    # Quantization
    parser.add_argument(
        "--no_4bit",
        action="store_true",
        help="Disable 4-bit quantization",
    )

    # Export options
    parser.add_argument(
        "--export_gguf",
        action="store_true",
        help="Export final model to GGUF format",
    )
    parser.add_argument(
        "--gguf_quantization",
        type=str,
        default="q4_k_m",
        choices=["q4_k_m", "q5_k_m", "q8_0", "f16"],
        help="GGUF quantization method",
    )

    # Logging and checkpointing
    parser.add_argument(
        "--logging_steps",
        type=int,
        default=1,
        help="Log metrics every N steps (default 1 for RL visibility)",
    )
    parser.add_argument(
        "--save_steps",
        type=int,
        default=50,
        help="Save checkpoint every N steps",
    )

    # Other
    parser.add_argument(
        "--seed",
        type=int,
        default=3407,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--install_mamba",
        action="store_true",
        help="Install mamba_ssm + causal_conv1d CUDA kernels at runtime "
        "(required for Granite 4.0 Mamba2 hybrid models)",
    )
    parser.add_argument(
        "--disable_dynamo",
        action="store_true",
        help="Set TORCHDYNAMO_DISABLE=1 to force eager execution. "
        "Required for models whose hybrid architecture causes "
        "torch.compile symbolic shape mismatches in Unsloth's "
        "chunked_hidden_states_selective_log_softmax.",
    )
    parser.add_argument(
        "--patch_lfm2_logps",
        action="store_true",
        help="Monkey-patch chunked_hidden_states_selective_log_softmax "
        "in Unsloth's compiled cache to handle LFM2 hybrid models "
        "whose hidden states arrive with vocab_size dimension instead "
        "of hidden_size.  Prefer --use_vllm when the vLLM environment "
        "is available.",
    )
    parser.add_argument(
        "--use_vllm",
        action="store_true",
        help="Use vLLM for GRPO generation (requires unsloth-vllm-training "
        "environment).  This takes vLLM's generation path and bypasses "
        "Unsloth's chunked_hidden_states_selective_log_softmax entirely, "
        "which is the official fix for LFM2 hybrid-architecture models. "
        "See: https://unsloth.ai/docs/models/tutorials/lfm2.5",
    )
    parser.add_argument(
        "--vllm_attention_backend",
        type=str,
        default="auto",
        choices=["auto", "flashinfer", "xformers", "flashattn", "sdpa"],
        help="vLLM attention backend selection. "
        "auto uses vLLM default except on pre-Ampere GPUs (<8.0), "
        "where it forces XFORMERS for compatibility.",
    )

    args = parser.parse_args()
    if args.install_mamba:
        install_mamba_kernels()

    # Validate arguments
    if args.num_generations < 2:
        parser.error("--num_generations must be >= 2 for GRPO advantage computation")

    if args.max_seq_length not in [2048, 4096, 8192, 16384, 32768]:
        print(
            f"⚠️ Warning: max_seq_length={args.max_seq_length} is unusual. "
            f"Recommended: 4096, 8192, 16384"
        )

    main(args)
