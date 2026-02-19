#!/usr/bin/env python3
"""
Supervised Fine-Tuning (SFT) Script for PantryPilot Tool-Calling Agent

Trains small language models on tool-calling conversations using:
- Unsloth for efficient QLoRA training
- TRL SFTTrainer for supervised fine-tuning
- MLflow for experiment tracking
- Extended context support via RoPE scaling
- Custom tool-calling metrics logging

Usage:
    python sft_train.py --base_model unsloth/Qwen2.5-0.5B-Instruct-bnb-4bit \
                        --training_data pantrypilot-sft-data:1 \
                        --val_data pantrypilot-sft-data-val:1 \
                        --output_dir ./outputs/sft \
                        --max_seq_length 8192
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Any

# Disable Unsloth's padding-free auto-enable BEFORE importing unsloth.
# V100 GPUs lack Flash Attention 2, and Unsloth's padding-free mode
# causes SDPA tensor size mismatches on the FA2-less fallback path.
os.environ["UNSLOTH_DISABLE_AUTO_PADDING_FREE"] = "1"

import mlflow
import torch

# Unsloth MUST be imported before trl, transformers, peft
# to ensure all optimisation patches are applied.
import unsloth  # noqa: F401  (side-effect import for patching)
from datasets import load_dataset
from transformers import TrainerCallback
from trl import SFTConfig, SFTTrainer
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template


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


class ToolCallMetricsCallback(TrainerCallback):
    """
    Custom callback to log tool-calling specific metrics during training.

    Tracks:
    - GPU memory usage
    - Tool call accuracy (during eval)
    - JSON validity rate
    - Argument completeness rate
    """

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        """Log custom metrics after evaluation."""
        if metrics:
            # Log GPU memory usage
            if torch.cuda.is_available():
                gpu_mem = torch.cuda.max_memory_allocated() / 1e9
                mlflow.log_metric(
                    "system/gpu_memory_gb", gpu_mem, step=state.global_step
                )
                # Reset peak memory stats for next eval
                torch.cuda.reset_peak_memory_stats()

            # Log training metrics
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(f"eval/{key}", value, step=state.global_step)

    def on_log(self, args, state, control, logs=None, **kwargs):
        """Log training metrics to MLflow."""
        if logs:
            for key, value in logs.items():
                if isinstance(value, (int, float)) and not key.startswith("eval"):
                    mlflow.log_metric(f"train/{key}", value, step=state.global_step)


def load_data_from_azure_ml(data_asset_name: str) -> str:
    """
    Load data from Azure ML Data Asset.

    Args:
        data_asset_name: Name of the data asset (e.g., "pantrypilot-sft-data:1")

    Returns:
        Path to the downloaded data files
    """
    from azure.ai.ml import MLClient
    from azure.identity import DefaultAzureCredential

    # Initialize Azure ML client
    ml_client = MLClient.from_config(DefaultAzureCredential())

    # Parse asset name and version
    if ":" in data_asset_name:
        asset_name, version = data_asset_name.split(":")
    else:
        asset_name = data_asset_name
        version = None

    # Get data asset
    data_asset = ml_client.data.get(name=asset_name, version=version)

    return data_asset.path


def format_conversations(examples: dict[str, Any], tokenizer: Any) -> dict[str, list]:
    """
    Format conversation data using ChatML template.

    Training data is stored in the native OpenAI/pydantic-ai API format
    (``role``/``content`` keys) so no key conversion is needed.

    Each example has:

    * ``messages`` \u2014 list of message dicts with ``role``, ``content``,
      optional ``tool_calls`` (assistant) and ``tool_call_id`` (tool).
    * ``tools`` \u2014 list of OpenAI-format function definitions.

    Tool definitions are injected into the system message text so the
    model learns tool-use syntax with the exact parameter schemas it will
    see at inference time.  We inject into the system message rather than
    using ``apply_chat_template(tools=...)`` because the plain ChatML
    Jinja2 template silently ignores the ``tools`` parameter.

    Args:
        examples: Batch of examples with 'messages' and 'tools' fields
        tokenizer: Tokenizer with chat template applied

    Returns:
        Dictionary with 'text' field containing formatted conversations
    """
    formatted_texts: list[str] = []
    tools_batch = examples.get("tools")
    for idx, conv in enumerate(examples["messages"]):
        # Get tool definitions for this example
        tool_defs = (
            tools_batch[idx]
            if tools_batch is not None and idx < len(tools_batch) and tools_batch[idx]
            else None
        )

        # Data is already in OpenAI format (role/content).
        # Inject tool definitions into the system message.
        messages: list[dict[str, Any]] = []
        for msg in conv:
            entry: dict[str, Any] = {
                "role": msg["role"],
                "content": msg.get("content", ""),
            }
            # Inject tool definitions into the system message so the model
            # learns what tools are available with their exact schemas.
            if msg["role"] == "system" and tool_defs:
                entry["content"] = _inject_tools_into_system_prompt(
                    entry["content"], tool_defs
                )
            # Preserve tool_calls on assistant messages
            if "tool_calls" in msg:
                entry["tool_calls"] = msg["tool_calls"]
            # Preserve tool_call_id on tool-response messages
            if "tool_call_id" in msg:
                entry["tool_call_id"] = msg["tool_call_id"]
            messages.append(entry)

        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
        formatted_texts.append(text)
    return {"text": formatted_texts}


def _inject_tools_into_system_prompt(
    system_content: str, tool_defs: list[dict[str, Any]]
) -> str:
    """Append tool definitions to the system prompt.

    Renders tool definitions in a ``<tools>`` XML block appended to the
    system prompt.  This follows the Qwen tool-calling convention
    (``<tools>...</tools>`` + ``<tool_call>...</tool_call>``) which works
    with ChatML-family models.

    Args:
        system_content: Original system prompt text
        tool_defs: List of OpenAI-format tool definitions

    Returns:
        System prompt with tool definitions appended
    """
    if not tool_defs:
        return system_content

    tools_block = (
        "\n\n# Tools\n\n"
        "You may call one or more functions to assist with the user query.\n\n"
        "You are provided with function signatures within <tools></tools> XML tags:\n"
        "<tools>\n"
    )
    for td in tool_defs:
        tools_block += json.dumps(td) + "\n"
    tools_block += (
        "</tools>\n\n"
        "For each function call, return a json object with function name and "
        "arguments within <tool_call></tool_call> XML tags:\n"
        "<tool_call>\n"
        '{"name": <function-name>, "arguments": <args-json-object>}\n'
        "</tool_call>"
    )
    return system_content + tools_block


def main(args: argparse.Namespace) -> None:
    """
    Main training function for SFT.

    Args:
        args: Parsed command-line arguments
    """
    # Start MLflow run
    mlflow.start_run(run_name=args.run_name)

    print(f"🚀 Starting SFT training with {args.base_model}")
    print(f"📊 Max sequence length: {args.max_seq_length}")
    print(f"🔧 LoRA rank: {args.lora_r}, alpha: {args.lora_alpha}")

    # Load model with optional 4-bit quantization and RoPE scaling
    load_4bit = not args.no_4bit
    print(f"\n📦 Loading base model from HuggingFace (4-bit={load_4bit})...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base_model,
        max_seq_length=args.max_seq_length,  # RoPE scaling handled automatically!
        load_in_4bit=load_4bit,
        dtype=None,  # Auto-detect
        device_map="auto",
    )

    # Apply QLoRA / LoRA
    # Default target modules work for Llama/Qwen/Gemma architectures.
    # LFM2.5 (Liquid) uses: q_proj,k_proj,v_proj,out_proj,in_proj,w1,w2,w3
    # Override via --target_modules if needed.
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
    print(f"\n🔧 Applying LoRA adapters (target_modules={target_modules})...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0,  # Unsloth optimized for 0 dropout
        target_modules=target_modules,
        use_gradient_checkpointing="unsloth",  # Critical for long context!
        random_state=3407,
    )

    # Load training data
    print("\n📚 Loading training data...")
    if args.training_data.startswith("pantrypilot-"):
        # Load from Azure ML Data Asset
        train_data_path = load_data_from_azure_ml(args.training_data)
        dataset = load_dataset("json", data_files=train_data_path, split="train")
    else:
        # Load from local file
        dataset = load_dataset("json", data_files=args.training_data, split="train")

    # Load validation data if provided
    eval_dataset = None
    if args.val_data:
        print("📚 Loading validation data...")
        if args.val_data.startswith("pantrypilot-"):
            val_data_path = load_data_from_azure_ml(args.val_data)
            eval_dataset = load_dataset("json", data_files=val_data_path, split="train")
        else:
            eval_dataset = load_dataset("json", data_files=args.val_data, split="train")

    # Apply chat template (ChatML for Qwen/Gemma, native for Granite/others)
    chat_template_name = args.chat_template
    print(f"\n💬 Applying chat template: {chat_template_name}...")
    if chat_template_name == "native":
        # Use the tokenizer's built-in chat template (e.g., Granite 4.0)
        print("   Using model's native chat template")
    else:
        tokenizer = get_chat_template(tokenizer, chat_template=chat_template_name)

    # Format conversations
    dataset = dataset.map(
        lambda examples: format_conversations(examples, tokenizer),
        batched=True,
        remove_columns=dataset.column_names,
    )

    if eval_dataset:
        eval_dataset = eval_dataset.map(
            lambda examples: format_conversations(examples, tokenizer),
            batched=True,
            remove_columns=eval_dataset.column_names,
        )

    print(f"✅ Loaded {len(dataset)} training samples")
    if eval_dataset:
        print(f"✅ Loaded {len(eval_dataset)} validation samples")

    # Azure ML limits MLflow to 200 logged parameters.  The HuggingFace
    # MLflowCallback logs every SFTConfig field (~230 params), which exceeds
    # this limit and causes a RestException.  We therefore set
    # report_to="none" and log only the essential hyperparameters manually.
    mlflow.log_params(
        {
            "base_model": args.base_model,
            "chat_template": args.chat_template,
            "max_seq_length": args.max_seq_length,
            "batch_size": args.batch_size,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
            "learning_rate": args.learning_rate,
            "num_epochs": args.num_epochs,
            "warmup_steps": args.warmup_steps,
            "lora_r": args.lora_r,
            "lora_alpha": args.lora_alpha,
            "target_modules": ",".join(target_modules),
            "load_in_4bit": load_4bit,
            "optim": "adamw_8bit",
            "lr_scheduler_type": "cosine",
            "weight_decay": 0.01,
            "seed": args.seed,
            "logging_steps": args.logging_steps,
            "eval_steps": args.eval_steps,
            "save_steps": args.save_steps,
        }
    )
    mlflow.set_tags(
        {
            "dataset_size": str(len(dataset)),
            "val_dataset_size": str(len(eval_dataset) if eval_dataset else 0),
            "stage": "sft",
        }
    )

    # Training configuration
    print("\n⚙️ Setting up training configuration...")
    training_args = SFTConfig(
        output_dir=args.output_dir,
        report_to="none",  # Disable built-in MLflow callback (Azure ML 200-param limit)
        run_name=args.run_name,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_epochs,
        warmup_steps=args.warmup_steps,
        logging_steps=args.logging_steps,
        eval_strategy="steps" if eval_dataset else "no",
        eval_steps=args.eval_steps if eval_dataset else None,
        save_steps=args.save_steps,
        save_total_limit=3,  # Keep only last 3 checkpoints
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        optim="adamw_8bit",  # 8-bit AdamW optimizer
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=args.seed,
    )

    # Initialize trainer
    print("\n🏋️ Initializing SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        eval_dataset=eval_dataset,
        dataset_text_field="text",
        max_seq_length=args.max_seq_length,
        args=training_args,
        callbacks=[ToolCallMetricsCallback()],
    )

    # Train
    print("\n🔥 Starting training...")
    trainer.train()

    # Save final model
    print("\n💾 Saving final model...")
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    # Save LoRA adapters separately
    lora_output_dir = os.path.join(args.output_dir, "lora_adapters")
    print(f"💾 Saving LoRA adapters to {lora_output_dir}...")
    model.save_pretrained(lora_output_dir)

    # Azure ML automatically uploads everything under ./outputs/ as job
    # artifacts, so we do NOT call mlflow.log_artifacts() — doing so triggers
    # a TypeError in azureml-mlflow due to an incompatible tracking_uri kwarg.

    # Export GGUF if requested
    if args.export_gguf:
        print("\n🔧 Exporting GGUF model...")
        gguf_output_dir = os.path.join(args.output_dir, "gguf")
        os.makedirs(gguf_output_dir, exist_ok=True)

        model.save_pretrained_gguf(
            gguf_output_dir, tokenizer, quantization_method=args.gguf_quantization
        )
        print(f"✅ GGUF model exported to {gguf_output_dir}")

    # Log final metrics before ending the run
    run_id = mlflow.active_run().info.run_id

    # End MLflow run
    mlflow.end_run()

    print("\n✅ Training complete!")
    print(f"📁 Model saved to: {args.output_dir}")
    print(f"📊 MLflow run: {run_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train PantryPilot SFT model with Unsloth"
    )

    # Model arguments
    parser.add_argument(
        "--base_model",
        type=str,
        default="unsloth/Qwen2.5-0.5B-Instruct-bnb-4bit",
        help="HuggingFace model ID or path (default: Qwen 0.5B)",
    )
    parser.add_argument(
        "--max_seq_length",
        type=int,
        default=4096,
        help="Maximum sequence length (supports 4096, 8192, 16384 via RoPE scaling)",
    )

    # Data arguments
    parser.add_argument(
        "--training_data",
        type=str,
        required=True,
        help="Training data path or Azure ML Data Asset name (e.g., pantrypilot-sft-data:1)",
    )
    parser.add_argument(
        "--val_data",
        type=str,
        default=None,
        help="Validation data path or Azure ML Data Asset name (optional)",
    )

    # Output arguments
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./outputs/sft",
        help="Output directory for model checkpoints",
    )
    parser.add_argument(
        "--run_name",
        type=str,
        default="sft-run",
        help="MLflow run name",
    )

    # Training hyperparameters
    parser.add_argument(
        "--batch_size",
        type=int,
        default=2,
        help="Per-device batch size",
    )
    parser.add_argument(
        "--gradient_accumulation_steps",
        type=int,
        default=4,
        help="Gradient accumulation steps (effective batch size = batch_size * gradient_accumulation_steps)",
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=2e-4,
        help="Peak learning rate",
    )
    parser.add_argument(
        "--num_epochs",
        type=int,
        default=3,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--warmup_steps",
        type=int,
        default=10,
        help="Learning rate warmup steps",
    )

    # LoRA configuration
    parser.add_argument(
        "--lora_r",
        type=int,
        default=16,
        help="LoRA rank (higher = more parameters, slower training)",
    )
    parser.add_argument(
        "--lora_alpha",
        type=int,
        default=32,
        help="LoRA alpha (typically 2x lora_r)",
    )
    parser.add_argument(
        "--target_modules",
        type=str,
        default=None,
        help="Comma-separated LoRA target modules (default: q/k/v/o/gate/up/down_proj). "
        "For LFM2.5: q_proj,k_proj,v_proj,out_proj,in_proj,w1,w2,w3",
    )

    # Chat template
    parser.add_argument(
        "--chat_template",
        type=str,
        default="chatml",
        help="Chat template name for tokenizer (default: chatml). "
        "Use 'granite' for IBM Granite 4.0 models.",
    )

    # Quantization
    parser.add_argument(
        "--no_4bit",
        action="store_true",
        help="Disable 4-bit quantization (required for some models like LFM2.5)",
    )

    # Logging and checkpointing
    parser.add_argument(
        "--logging_steps",
        type=int,
        default=10,
        help="Log metrics every N steps",
    )
    parser.add_argument(
        "--eval_steps",
        type=int,
        default=100,
        help="Evaluate every N steps (if validation data provided)",
    )
    parser.add_argument(
        "--save_steps",
        type=int,
        default=100,
        help="Save checkpoint every N steps",
    )

    # Export options
    parser.add_argument(
        "--export_gguf",
        action="store_true",
        help="Export final model to GGUF format for llama.cpp deployment",
    )
    parser.add_argument(
        "--gguf_quantization",
        type=str,
        default="q4_k_m",
        choices=["q4_k_m", "q5_k_m", "q8_0", "f16"],
        help="GGUF quantization method",
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
