#!/usr/bin/env python3
"""
Domain-Adaptive Pre-Training (DAPT) Script for PantryPilot Culinary SLM

Continues pre-training a base language model on a culinary-domain corpus
using causal language modeling (CLM).  No chat template is applied – the
model simply learns to predict the next token on domain-specific text.

Workflow:
    DAPT (this script) → SFT (sft_train.py) → GRPO (grpo_train.py)

Corpus format (JSONL):
    {"text": "# Chocolate Chip Cookies\\n\\nCategory: desserts ..."}

Supported base models for DAPT:
    - unsloth/Qwen3-0.6B-Base-unsloth-bnb-4bit   (default, 0.6B params)
    - unsloth/Qwen3-1.7B-Base-unsloth-bnb-4bit   (1.7B params)

    DAPT uses BASE models (not instruct-tuned) since we are continuing
    pre-training before SFT.  The pipeline is: Base → DAPT → SFT → GRPO.

Usage:
    python dapt_train.py \
        --base_model unsloth/Qwen3-0.6B-Base-unsloth-bnb-4bit \
        --training_data dapt-culinary-corpus:1 \
        --output_dir ./outputs/dapt \
        --max_seq_length 2048 \
        --batch_size 4

    # With streaming for very large corpora:
    python dapt_train.py \
        --base_model unsloth/Qwen3-1.7B-Base-unsloth-bnb-4bit \
        --training_data dapt-culinary-corpus:1 \
        --output_dir ./outputs/dapt \
        --streaming
"""

import argparse
import os

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


class DAPTMetricsCallback(TrainerCallback):
    """Callback to log DAPT-specific metrics to MLflow.

    Tracks GPU memory usage and per-step training loss.
    """

    def on_log(self, args, state, control, logs=None, **kwargs):
        """Forward training metrics to MLflow."""
        if logs:
            for key, value in logs.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(f"train/{key}", value, step=state.global_step)

            # Log GPU memory periodically
            if torch.cuda.is_available() and state.global_step % 50 == 0:
                gpu_mem = torch.cuda.max_memory_allocated() / 1e9
                mlflow.log_metric(
                    "system/gpu_memory_gb", gpu_mem, step=state.global_step
                )


def load_data_from_azure_ml(data_asset_name: str) -> str:
    """Resolve an Azure ML Data Asset reference to a local/mounted path.

    Args:
        data_asset_name: Asset name with optional version (e.g. "dapt-culinary-corpus:1").

    Returns:
        File-system path to the data.
    """
    from azure.ai.ml import MLClient
    from azure.identity import DefaultAzureCredential

    ml_client = MLClient.from_config(DefaultAzureCredential())

    if ":" in data_asset_name:
        asset_name, version = data_asset_name.split(":")
    else:
        asset_name = data_asset_name
        version = None

    data_asset = ml_client.data.get(name=asset_name, version=version)
    return data_asset.path


def main(args: argparse.Namespace) -> None:
    """Run DAPT with causal language modeling."""
    mlflow.start_run(run_name=args.run_name)

    print(f"🚀 Starting DAPT with {args.base_model}")
    print(f"📊 Max sequence length: {args.max_seq_length}")
    print(f"🔧 LoRA rank: {args.lora_r}, alpha: {args.lora_alpha}")
    print(f"📡 Streaming: {args.streaming}")

    # ------------------------------------------------------------------
    # 1. Load base model
    # ------------------------------------------------------------------
    load_4bit = not args.no_4bit
    print(f"\n📦 Loading base model (4-bit={load_4bit})...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base_model,
        max_seq_length=args.max_seq_length,
        load_in_4bit=load_4bit,
        dtype=None,
        device_map="auto",
    )

    # ------------------------------------------------------------------
    # 2. Apply LoRA adapters
    # ------------------------------------------------------------------
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
        lora_dropout=0,
        target_modules=target_modules,
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    # ------------------------------------------------------------------
    # 3. Load corpus data
    # ------------------------------------------------------------------
    print("\n📚 Loading corpus data...")
    data_path: str | None = None

    if args.training_data.startswith("dapt-") or args.training_data.startswith(
        "pantrypilot-"
    ):
        data_path = load_data_from_azure_ml(args.training_data)
    else:
        data_path = args.training_data

    if args.streaming:
        # Streaming mode – memory-efficient for large corpora (150M+ tokens)
        dataset = load_dataset(
            "json",
            data_files=data_path,
            split="train",
            streaming=True,
        )

        # Workaround: Unsloth's SFTTrainer._prepare_dataset accesses
        # dataset._ex_iterable.batch_size, but ArrowExamplesIterable
        # (used for local JSONL files) lacks that attribute.
        if hasattr(dataset, "_ex_iterable") and not hasattr(
            dataset._ex_iterable, "batch_size"
        ):
            dataset._ex_iterable.batch_size = 1000

        # Count is unknown in streaming mode
        dataset_size = "streaming (size unknown)"
        print(f"✅ Loaded dataset in streaming mode from {data_path}")
    else:
        dataset = load_dataset("json", data_files=data_path, split="train")
        dataset_size = len(dataset)
        print(f"✅ Loaded {dataset_size} documents from {data_path}")

    # ------------------------------------------------------------------
    # 4. Log hyperparameters
    # ------------------------------------------------------------------
    # Azure ML limits MLflow to 200 logged parameters.  The HuggingFace
    # MLflowCallback logs every SFTConfig field (~230 params), which exceeds
    # this limit and causes a RestException.  We therefore set
    # report_to="none" and log only the essential hyperparameters manually.
    mlflow.log_params(
        {
            "base_model": args.base_model,
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
            "save_steps": args.save_steps,
            "streaming": args.streaming,
            "max_steps": args.max_steps if args.streaming else -1,
        }
    )
    mlflow.set_tags(
        {
            "dataset_size": str(dataset_size),
            "stage": "dapt",
        }
    )

    # ------------------------------------------------------------------
    # 5. Training configuration
    # ------------------------------------------------------------------
    print("\n⚙️ Setting up training configuration...")

    # For streaming datasets max_steps must be set; num_train_epochs is ignored.
    max_steps = args.max_steps if args.streaming else -1

    training_args = SFTConfig(
        output_dir=args.output_dir,
        report_to="none",  # Disable built-in MLflow callback (Azure ML 200-param limit)
        run_name=args.run_name,
        # Batching
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        # Schedule
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_epochs if not args.streaming else 1,
        max_steps=max_steps,
        warmup_steps=args.warmup_steps,
        lr_scheduler_type="cosine",
        # Logging & checkpoints
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=3,
        # Precision
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        # Optimiser
        optim="adamw_8bit",
        weight_decay=0.01,
        seed=args.seed,
        # DAPT has no eval phase
        eval_strategy="no",
    )

    # ------------------------------------------------------------------
    # 6. Initialise trainer
    # ------------------------------------------------------------------
    print("\n🏋️ Initializing SFTTrainer for DAPT (CLM)...")

    # DAPT uses plain ``text`` field directly – no chat template formatting.
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=args.max_seq_length,
        args=training_args,
        callbacks=[DAPTMetricsCallback()],
    )

    # ------------------------------------------------------------------
    # 7. Train
    # ------------------------------------------------------------------
    print("\n🔥 Starting DAPT training...")
    trainer.train()

    # ------------------------------------------------------------------
    # 8. Save checkpoint for SFT stage
    # ------------------------------------------------------------------
    print("\n💾 Saving DAPT checkpoint...")
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    # Save LoRA adapters separately (needed for pipeline stage handoff)
    lora_dir = os.path.join(args.output_dir, "lora_adapters")
    print(f"💾 Saving LoRA adapters to {lora_dir}...")
    model.save_pretrained(lora_dir)

    # Azure ML automatically uploads everything under ./outputs/ as job
    # artifacts, so we do NOT call mlflow.log_artifacts() — doing so triggers
    # a TypeError in azureml-mlflow due to an incompatible tracking_uri kwarg.

    # Log final metrics before ending the run
    run_id = mlflow.active_run().info.run_id

    mlflow.end_run()

    print("\n✅ DAPT training complete!")
    print(f"📁 Checkpoint saved to: {args.output_dir}")
    print(f"📊 MLflow run: {run_id}")
    print("   → Use this checkpoint as --base_model for sft_train.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Domain-Adaptive Pre-Training (DAPT) for PantryPilot culinary SLM"
    )

    # Model arguments
    parser.add_argument(
        "--base_model",
        type=str,
        default="unsloth/Qwen3-0.6B-Base-unsloth-bnb-4bit",
        help="HuggingFace base model ID or local path (use base models, not instruct)",
    )
    parser.add_argument(
        "--max_seq_length",
        type=int,
        default=2048,
        help="Maximum sequence length for training",
    )

    # Data arguments
    parser.add_argument(
        "--training_data",
        type=str,
        required=True,
        help="Corpus path or Azure ML Data Asset name (e.g. dapt-culinary-corpus:1)",
    )
    parser.add_argument(
        "--streaming",
        action="store_true",
        help="Use streaming data loading for large corpora (memory-efficient)",
    )
    parser.add_argument(
        "--max_steps",
        type=int,
        default=10000,
        help="Max training steps when using --streaming (ignored otherwise)",
    )

    # Output
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./outputs/dapt",
        help="Output directory for checkpoints",
    )
    parser.add_argument(
        "--run_name",
        type=str,
        default="dapt-run",
        help="MLflow run name",
    )

    # Training hyperparameters
    parser.add_argument(
        "--batch_size",
        type=int,
        default=4,
        help="Per-device batch size (DAPT can use larger batches than SFT)",
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
        default=2e-5,
        help="Peak learning rate (lower than SFT to preserve base knowledge)",
    )
    parser.add_argument(
        "--num_epochs",
        type=int,
        default=1,
        help="Number of epochs (1 is typical for DAPT on large corpora)",
    )
    parser.add_argument(
        "--warmup_steps",
        type=int,
        default=100,
        help="Learning rate warmup steps",
    )

    # LoRA configuration
    parser.add_argument(
        "--lora_r",
        type=int,
        default=16,
        help="LoRA rank",
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
        help="Comma-separated LoRA target modules (default: q/k/v/o/gate/up/down_proj)",
    )

    # Quantization
    parser.add_argument(
        "--no_4bit",
        action="store_true",
        help="Disable 4-bit quantization",
    )

    # Logging & checkpoints
    parser.add_argument(
        "--logging_steps",
        type=int,
        default=10,
        help="Log metrics every N steps",
    )
    parser.add_argument(
        "--save_steps",
        type=int,
        default=500,
        help="Save checkpoint every N steps",
    )

    # Other
    parser.add_argument(
        "--seed",
        type=int,
        default=3407,
        help="Random seed for reproducibility",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.max_seq_length not in [2048, 4096, 8192, 16384, 32768]:
        print(
            f"⚠️ Warning: max_seq_length={args.max_seq_length} is unusual. "
            f"Recommended: 2048, 4096, 8192"
        )

    main(args)
