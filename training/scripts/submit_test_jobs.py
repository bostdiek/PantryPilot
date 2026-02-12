#!/usr/bin/env python3
"""Submit SFT validation test jobs to Azure ML.

Submits short training runs on the validation dataset only to verify
that training works correctly on the GPU cluster for each base model.

Prerequisites:
    1. Azure CLI logged in: `az login`
    2. Azure ML extension: `az extension add -n ml`
    3. Training data uploaded: `uv run python apps/backend/scripts/upload_training_data.py`

Usage:
    # Test all models
    uv run python training/scripts/submit_test_jobs.py --all-models

    # Test specific model
    uv run python training/scripts/submit_test_jobs.py --model unsloth/Qwen2.5-0.5B-Instruct-bnb-4bit

    # Dry run (show what would be submitted)
    uv run python training/scripts/submit_test_jobs.py --all-models --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from azure.ai.ml import MLClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Models to test - loaded directly from HuggingFace via Unsloth
# See https://unsloth.ai/docs/models for supported models
# Per-model overrides are applied on top of DEFAULT_CONFIG.
TEST_MODELS: dict[str, dict] = {
    "qwen-0.5b": {
        "model_id": "unsloth/Qwen2.5-0.5B-Instruct-bnb-4bit",
    },
    "qwen-1.5b": {
        "model_id": "unsloth/Qwen2.5-1.5B-Instruct-bnb-4bit",
    },
    "qwen3-0.6b": {
        # Docs: https://unsloth.ai/docs/models/tutorials/qwen3
        # Qwen3 architecture with improved agent/tool-calling capabilities
        "model_id": "unsloth/Qwen3-0.6B-unsloth-bnb-4bit",
        "max_seq_length": 4096,  # OOM at 8192 on V100 16GB (larger hidden dim than Qwen2.5-0.5B)
    },
    "qwen3-1.7b": {
        # Qwen3 1.7B - larger Qwen3 to see if architecture gains scale
        "model_id": "unsloth/Qwen3-1.7B-unsloth-bnb-4bit",
        "max_seq_length": 4096,  # Conservative for V100 16GB
    },
    # "granite-350m": {
    #     # DISABLED: V100 cluster incompatible — NaN loss (fp16-only, no bf16),
    #     # mamba_ssm won't compile (system CUDA 11.8 vs PyTorch cu128), and
    #     # no prebuilt wheel for torch 2.10.  Three independent blockers.
    #     # Docs: https://unsloth.ai/docs/models/tutorials/ibm-granite-4.0
    #     # Official notebook: https://github.com/unslothai/notebooks/blob/main/nb/Granite4.0_350M.ipynb
    #     "model_id": "unsloth/granite-4.0-350m",
    #     "chat_template": "native",
    #     "install_mamba": True,
    #     "no_4bit": True,
    #     "target_modules": "q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj,shared_mlp.input_linear,shared_mlp.output_linear",
    #     "lora_r": 32,
    #     "lora_alpha": 32,
    #     "max_seq_length": 2048,
    #     "learning_rate": 2e-4,
    # },
    "liquid-1.2b": {
        # Docs: https://unsloth.ai/docs/models/tutorials/lfm2.5
        "model_id": "LiquidAI/LFM2.5-1.2B-Instruct",
        "no_4bit": True,  # LFM2.5 does not support 4-bit loading
        "target_modules": "q_proj,k_proj,v_proj,out_proj,in_proj,w1,w2,w3",
        "lora_r": 16,
        "max_seq_length": 4096,  # Recommended in Unsloth docs
    },
    "fgemma-270m": {
        "model_id": "unsloth/functiongemma-270m-it",
    },
}

# Default training configuration for validation test
DEFAULT_CONFIG = {
    "max_seq_length": 8192,  # 86.7% coverage, safe for V100 16GB
    "batch_size": 1,
    "gradient_accumulation_steps": 4,
    "learning_rate": 2e-4,
    "num_epochs": 1,
    "warmup_steps": 5,
    "lora_r": 8,  # Lower rank for faster testing
    "lora_alpha": 16,
    "logging_steps": 5,
    "eval_steps": 25,
    "save_steps": 50,
}


def load_workspace_config() -> tuple[str, str, str]:
    """Load Azure ML workspace configuration from config.json."""
    config_path = Path(__file__).parent.parent.parent / "config.json"
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    return (
        config["subscription_id"],
        config["resource_group"],
        config["workspace_name"],
    )


def create_ml_client() -> MLClient:
    """Create Azure ML client using workspace configuration."""
    try:
        from azure.ai.ml import MLClient
        from azure.identity import DefaultAzureCredential
    except ImportError as e:
        logger.error(
            "Azure ML SDK not installed. Install with:\n"
            "  cd apps/backend && uv sync --group training"
        )
        raise SystemExit(1) from e

    subscription_id, resource_group, workspace_name = load_workspace_config()

    logger.info(f"Connecting to workspace: {workspace_name}")

    credential = DefaultAzureCredential()
    return MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )


def get_training_data_versions(ml_client: MLClient) -> tuple[str, str]:
    """Get latest versions of training and validation data assets.

    Returns:
        Tuple of (train_data_ref, val_data_ref)
    """
    try:
        # Get latest versions
        train_assets = list(ml_client.data.list(name="pantrypilot-sft-data"))
        val_assets = list(ml_client.data.list(name="pantrypilot-sft-data-val"))

        if not train_assets:
            raise ValueError("Training data asset 'pantrypilot-sft-data' not found")
        if not val_assets:
            raise ValueError(
                "Validation data asset 'pantrypilot-sft-data-val' not found"
            )

        # Get latest version by sorting
        latest_train = sorted(train_assets, key=lambda x: int(x.version))[-1]
        latest_val = sorted(val_assets, key=lambda x: int(x.version))[-1]

        train_ref = f"azureml:pantrypilot-sft-data:{latest_train.version}"
        val_ref = f"azureml:pantrypilot-sft-data-val:{latest_val.version}"

        logger.info(f"Using training data: {train_ref}")
        logger.info(f"Using validation data: {val_ref}")

        return train_ref, val_ref

    except Exception as e:
        logger.error(f"Failed to get training data: {e}")
        logger.error(
            "Make sure to upload training data first:\n"
            "  cd apps/backend && uv run python scripts/upload_training_data.py"
        )
        raise


def submit_test_job(
    ml_client: MLClient,
    model_name: str,
    model_id: str,
    train_data: str,
    val_data: str,
    config: dict,
    model_overrides: dict | None = None,
    dry_run: bool = False,
) -> str | None:
    """Submit a test training job to Azure ML.

    Args:
        ml_client: Azure ML client
        model_name: Short name for the model (e.g., 'qwen-0.5b')
        model_id: HuggingFace model ID
        train_data: Training data asset reference
        val_data: Validation data asset reference
        config: Training configuration
        model_overrides: Model-specific overrides (no_4bit, target_modules, etc.)
        dry_run: If True, don't actually submit

    Returns:
        Job name if submitted, None if dry run
    """
    from azure.ai.ml import Input, command
    from azure.ai.ml.constants import AssetTypes, InputOutputModes

    overrides = model_overrides or {}
    job_name = f"sft-test-{model_name}"

    # Get project root path (two levels up from this script)
    project_root = Path(__file__).parent.parent.parent.resolve()
    training_dir = project_root / "training"

    # Build command - packages are already in unsloth-training environment
    cmd = (
        "python scripts/sft_train.py "
        f"--base_model {model_id} "
        f"--training_data ${{{{inputs.train_data}}}} "
        f"--val_data ${{{{inputs.val_data}}}} "
        f"--output_dir ./outputs/{model_name} "
        f"--run_name {job_name} "
        f"--max_seq_length {config['max_seq_length']} "
        f"--batch_size {config['batch_size']} "
        f"--gradient_accumulation_steps {config['gradient_accumulation_steps']} "
        f"--learning_rate {config['learning_rate']} "
        f"--num_epochs {config['num_epochs']} "
        f"--warmup_steps {config['warmup_steps']} "
        f"--lora_r {config['lora_r']} "
        f"--lora_alpha {config['lora_alpha']} "
        f"--logging_steps {config['logging_steps']} "
        f"--eval_steps {config['eval_steps']} "
        f"--save_steps {config['save_steps']} "
    )

    # Append model-specific flags
    if overrides.get("install_mamba"):
        cmd += "--install_mamba "
    if overrides.get("no_4bit"):
        cmd += "--no_4bit "
    if overrides.get("target_modules"):
        cmd += f"--target_modules {overrides['target_modules']} "
    if overrides.get("chat_template"):
        cmd += f"--chat_template {overrides['chat_template']} "

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Model: {model_name} ({model_id})")
    logger.info(f"Job: {job_name}")
    logger.info(f"Config: {json.dumps(config, indent=2)}")

    if dry_run:
        logger.info("DRY RUN - Would submit job with command:")
        logger.info(cmd)
        return None

    # Create command job
    job = command(
        display_name=f"SFT Test: {model_name}",
        description=f"Validation test for {model_id}",
        experiment_name="pantrypilot-sft-validation",
        code=str(training_dir),  # Upload training directory
        command=cmd,
        inputs={
            "train_data": Input(
                type=AssetTypes.URI_FILE,
                path=train_data,
                mode=InputOutputModes.RO_MOUNT,
            ),
            "val_data": Input(
                type=AssetTypes.URI_FILE,
                path=val_data,
                mode=InputOutputModes.RO_MOUNT,
            ),
        },
        environment="unsloth-training@latest",  # Uses latest version with all packages
        compute="gpu-cluster",
        instance_count=1,
        tags={
            "model": model_id,
            "purpose": "validation-test",
        },
    )

    # Submit job
    logger.info("Submitting job...")
    submitted_job = ml_client.jobs.create_or_update(job)

    logger.info(f"✅ Job submitted: {submitted_job.name}")
    logger.info(f"   Status: {submitted_job.status}")
    logger.info(f"   URL: {submitted_job.studio_url}")

    return submitted_job.name


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Submit SFT validation test jobs to Azure ML"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Specific model ID to test (HuggingFace model ID)",
    )
    parser.add_argument(
        "--all-models",
        action="store_true",
        help="Test all supported models",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be submitted without actually submitting",
    )
    parser.add_argument(
        "--max-seq-length",
        type=int,
        default=DEFAULT_CONFIG["max_seq_length"],
        help="Maximum sequence length",
    )
    parser.add_argument(
        "--num-epochs",
        type=int,
        default=DEFAULT_CONFIG["num_epochs"],
        help="Number of epochs (default: 1 for quick test)",
    )

    args = parser.parse_args()

    if not args.model and not args.all_models:
        parser.error("Specify --model <model_id> or --all-models")

    # Create config with any overrides
    config = DEFAULT_CONFIG.copy()
    config["max_seq_length"] = args.max_seq_length
    config["num_epochs"] = args.num_epochs

    # Connect to Azure ML
    ml_client = create_ml_client()

    # Get training data
    train_data, val_data = get_training_data_versions(ml_client)

    # Determine models to test
    if args.all_models:
        models_to_test = TEST_MODELS
    else:
        # Single model specified
        model_id = args.model
        # Try to find matching entry in TEST_MODELS to get all overrides
        model_name = None
        matched_cfg = None
        for name, model_cfg in TEST_MODELS.items():
            if model_cfg["model_id"] == model_id:
                model_name = name
                matched_cfg = model_cfg
                break
        if model_name and matched_cfg:
            models_to_test = {model_name: matched_cfg}
        else:
            # Unknown model - use defaults with just the model_id
            model_name = model_id.split("/")[-1].lower().replace(".", "-")
            models_to_test = {model_name: {"model_id": model_id}}

    # Submit jobs
    submitted_jobs = []
    for model_name, model_cfg in models_to_test.items():
        model_id = model_cfg["model_id"]

        # Merge per-model config overrides into the base config
        job_config = config.copy()
        for key in ("max_seq_length", "lora_r", "lora_alpha", "learning_rate"):
            if key in model_cfg:
                job_config[key] = model_cfg[key]

        try:
            job_name = submit_test_job(
                ml_client,
                model_name,
                model_id,
                train_data,
                val_data,
                job_config,
                model_overrides=model_cfg,
                dry_run=args.dry_run,
            )
            if job_name:
                submitted_jobs.append(job_name)
        except Exception as e:
            logger.error(f"Failed to submit job for {model_name}: {e}")
            continue

    # Summary
    print(f"\n{'=' * 60}")
    if args.dry_run:
        print(f"DRY RUN: Would have submitted {len(models_to_test)} jobs")
    else:
        print(f"Submitted {len(submitted_jobs)} jobs:")
        for job in submitted_jobs:
            print(f"  - {job}")
        print("\nMonitor jobs in Azure ML Studio or with:")
        print("  az ml job show --name <job-name>")

    return 0


if __name__ == "__main__":
    sys.exit(main())
