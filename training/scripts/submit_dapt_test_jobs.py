#!/usr/bin/env python3
"""Submit DAPT validation test jobs to Azure ML.

Submits short DAPT training runs to verify that domain-adaptive
pre-training works correctly on the GPU cluster for each base model.
Uses a small max_steps to avoid burning compute — just enough to
confirm the pipeline runs end-to-end.

Prerequisites:
    1. Azure CLI logged in: `az login`
    2. Azure ML extension: `az extension add -n ml`
    3. DAPT corpus uploaded:
       `cd apps/backend && uv run python src/training/dapt/upload_to_azure.py --corpus data/commercial_culinary_corpus.jsonl`

Usage:
    # Test all models
    uv run python training/scripts/submit_dapt_test_jobs.py --all-models

    # Test specific model
    uv run python training/scripts/submit_dapt_test_jobs.py --model unsloth/Qwen2.5-0.5B-Instruct-bnb-4bit

    # Dry run (show what would be submitted)
    uv run python training/scripts/submit_dapt_test_jobs.py --all-models --dry-run
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

# DAPT uses BASE models (not instruct-tuned) since we are continuing
# pre-training before instruction tuning.  Pipeline: Base → DAPT → SFT → GRPO.
# Per-model overrides are applied on top of DEFAULT_CONFIG.
TEST_MODELS: dict[str, dict] = {
    "qwen3-0.6b-base": {
        "model_id": "unsloth/Qwen3-0.6B-Base-unsloth-bnb-4bit",
    },
    "qwen3-1.7b-base": {
        "model_id": "unsloth/Qwen3-1.7B-Base-unsloth-bnb-4bit",
        "max_seq_length": 2048,  # Conservative for V100 16GB with DAPT batch size
    },
}

# Default DAPT training configuration — small test runs.
# DAPT uses larger batch sizes and lower LR than SFT.
DEFAULT_CONFIG = {
    "max_seq_length": 2048,  # DAPT doesn't need long context
    "batch_size": 4,  # Larger batches for CLM
    "gradient_accumulation_steps": 4,
    "learning_rate": 2e-5,  # Lower LR to preserve base knowledge
    "num_epochs": 1,
    "warmup_steps": 10,
    "lora_r": 16,
    "lora_alpha": 32,
    "logging_steps": 5,
    "save_steps": 50,
    "max_steps": 50,  # Very small — just verify the pipeline works
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


def get_corpus_data_version(ml_client: MLClient) -> str:
    """Get latest version of DAPT corpus data asset.

    Returns:
        Azure ML data asset reference string.
    """
    try:
        corpus_assets = list(ml_client.data.list(name="dapt-culinary-corpus"))

        if not corpus_assets:
            raise ValueError("DAPT corpus asset 'dapt-culinary-corpus' not found")

        latest = sorted(corpus_assets, key=lambda x: int(x.version))[-1]
        corpus_ref = f"azureml:dapt-culinary-corpus:{latest.version}"

        logger.info(f"Using DAPT corpus: {corpus_ref}")
        return corpus_ref

    except Exception as e:
        logger.error(f"Failed to get DAPT corpus: {e}")
        logger.error(
            "Make sure to upload the corpus first:\n"
            "  cd apps/backend && uv run python src/training/dapt/upload_to_azure.py "
            "--corpus data/commercial_culinary_corpus.jsonl"
        )
        raise


def submit_dapt_test_job(
    ml_client: MLClient,
    model_name: str,
    model_id: str,
    corpus_data: str,
    config: dict,
    model_overrides: dict | None = None,
    dry_run: bool = False,
) -> str | None:
    """Submit a DAPT test training job to Azure ML.

    Args:
        ml_client: Azure ML client
        model_name: Short name for the model (e.g., 'qwen-0.5b')
        model_id: HuggingFace model ID
        corpus_data: DAPT corpus data asset reference
        config: Training configuration
        model_overrides: Model-specific overrides (no_4bit, target_modules, etc.)
        dry_run: If True, don't actually submit

    Returns:
        Job name if submitted, None if dry run
    """
    from azure.ai.ml import Input, command
    from azure.ai.ml.constants import AssetTypes, InputOutputModes

    overrides = model_overrides or {}
    job_name = f"dapt-test-{model_name}"

    # Get project root path (two levels up from this script)
    project_root = Path(__file__).parent.parent.parent.resolve()
    training_dir = project_root / "training"

    # Build command — uses streaming mode with small max_steps for quick validation
    cmd = (
        "python scripts/dapt_train.py "
        f"--base_model {model_id} "
        f"--training_data ${{{{inputs.corpus_data}}}} "
        f"--output_dir ./outputs/{model_name} "
        f"--run_name {job_name} "
        f"--max_seq_length {config['max_seq_length']} "
        f"--batch_size {config['batch_size']} "
        f"--gradient_accumulation_steps {config['gradient_accumulation_steps']} "
        f"--learning_rate {config['learning_rate']} "
        f"--warmup_steps {config['warmup_steps']} "
        f"--lora_r {config['lora_r']} "
        f"--lora_alpha {config['lora_alpha']} "
        f"--logging_steps {config['logging_steps']} "
        f"--save_steps {config['save_steps']} "
        f"--streaming "
        f"--max_steps {config['max_steps']} "
    )

    # Append model-specific flags
    if overrides.get("no_4bit"):
        cmd += "--no_4bit "
    if overrides.get("target_modules"):
        cmd += f"--target_modules {overrides['target_modules']} "

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
        display_name=f"DAPT Test: {model_name}",
        description=f"DAPT validation test for {model_id} ({config['max_steps']} steps)",
        experiment_name="pantrypilot-dapt-validation",
        code=str(training_dir),
        command=cmd,
        inputs={
            "corpus_data": Input(
                type=AssetTypes.URI_FILE,
                path=corpus_data,
                mode=InputOutputModes.RO_MOUNT,
            ),
        },
        environment="unsloth-training@latest",
        compute="gpu-cluster",
        instance_count=1,
        tags={
            "model": model_id,
            "purpose": "dapt-validation-test",
            "max_steps": str(config["max_steps"]),
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
        description="Submit DAPT validation test jobs to Azure ML"
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
        "--max-steps",
        type=int,
        default=DEFAULT_CONFIG["max_steps"],
        help=f"Max training steps (default: {DEFAULT_CONFIG['max_steps']})",
    )
    parser.add_argument(
        "--max-seq-length",
        type=int,
        default=DEFAULT_CONFIG["max_seq_length"],
        help="Maximum sequence length",
    )

    args = parser.parse_args()

    if not args.model and not args.all_models:
        parser.error("Specify --model <model_id> or --all-models")

    # Create config with any overrides
    config = DEFAULT_CONFIG.copy()
    config["max_steps"] = args.max_steps
    config["max_seq_length"] = args.max_seq_length

    # Connect to Azure ML
    ml_client = create_ml_client()

    # Get DAPT corpus data asset
    corpus_data = get_corpus_data_version(ml_client)

    # Determine models to test
    if args.all_models:
        models_to_test = TEST_MODELS
    else:
        model_id = args.model
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
            job_name = submit_dapt_test_job(
                ml_client,
                model_name,
                model_id,
                corpus_data,
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
