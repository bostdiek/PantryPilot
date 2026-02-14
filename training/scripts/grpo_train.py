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

import mlflow
import torch

# Unsloth MUST be imported before trl, transformers, peft
# to ensure all optimisation patches are applied.
import unsloth  # noqa: F401  (side-effect import for patching)
from datasets import Dataset
from reward_functions import ToolCallRewardComputer
from trl import GRPOConfig, GRPOTrainer
from unsloth import FastLanguageModel


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


def load_prompts(prompts_path: str) -> Dataset:
    """Load GRPO prompts from JSON file.

    The prompts file should contain an array of objects with at minimum
    a "prompt" field. Additional fields ("expected_tool", "category",
    "expected_args", "expected_query_keywords") are used by the reward
    function but not passed to the trainer.

    Args:
        prompts_path: Path to grpo_prompts.json

    Returns:
        HuggingFace Dataset with "prompt" column
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

    # Build prompt dataset — GRPOTrainer expects a "prompt" column
    # We store the full prompt data for reward function access
    prompts = []
    for item in raw_prompts:
        prompts.append(
            {
                "prompt": item["prompt"],
                "expected_tool": item.get("expected_tool"),
                "category": item.get("category", "unknown"),
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
        completions: list[str], prompts: list[str] | None = None
    ) -> list[float]:
        """Compute rewards for a batch of completions."""
        rewards = []
        for i, completion in enumerate(completions):
            prompt = prompts[i] if prompts else ""
            expected_tool = prompt_to_expected.get(prompt)
            score = reward_computer.compute_total_reward(
                completion=completion,
                prompt=prompt,
                expected_tool=expected_tool,
            )
            rewards.append(score)
        return rewards

    return reward_fn


def main(args: argparse.Namespace) -> None:
    """Main GRPO training function."""
    # Start MLflow run
    mlflow.start_run(run_name=args.run_name)

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
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base_model,
        max_seq_length=args.max_seq_length,
        load_in_4bit=load_4bit,
        dtype=None,  # Auto-detect
        device_map="auto",
    )

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
    prompt_dataset, raw_prompts = load_prompts(args.prompts_path)
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
    training_args = GRPOConfig(
        output_dir=args.output_dir,
        report_to="none",  # Disable built-in MLflow (Azure ML 200-param limit)
        run_name=args.run_name,
        num_generations=args.num_generations,
        temperature=args.temperature,
        max_new_tokens=args.max_new_tokens,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        beta=args.beta,
        num_train_epochs=args.num_epochs,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=3,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        seed=args.seed,
    )

    # Initialize GRPO trainer
    print("\n🏋️ Initializing GRPOTrainer...")
    trainer = GRPOTrainer(
        model=model,
        tokenizer=tokenizer,
        args=training_args,
        train_dataset=prompt_dataset,
        reward_funcs=[reward_fn],
    )

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
        default=4,
        help="Number of completions generated per prompt for group comparison",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature for generation",
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
        default=1,
        help="Number of training epochs",
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

    args = parser.parse_args()

    # Install Mamba kernels before any model loading if requested
    if args.install_mamba:
        install_mamba_kernels()

    # Validate arguments
    if args.max_seq_length not in [2048, 4096, 8192, 16384, 32768]:
        print(
            f"⚠️ Warning: max_seq_length={args.max_seq_length} is unusual. "
            f"Recommended: 4096, 8192, 16384"
        )

    main(args)
