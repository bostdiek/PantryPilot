#!/usr/bin/env python3
"""Submit GRPO training jobs to Azure ML.

Submits GRPO reinforcement learning jobs that optimise tool-calling
behaviour using reward signals from ToolCallRewardComputer.

Uses base HuggingFace models directly.  In later pipeline stages the
SFT checkpoint will be piped in automatically.

Pipeline position: DAPT → SFT → **GRPO**

Prerequisites:
    1. Azure CLI logged in: `az login`
    2. Azure ML extension: `az extension add -n ml`
    3. GRPO prompts file: training/data/grpo_prompts.json

Usage:
    # Submit jobs for both models
    uv run python training/scripts/submit_grpo_jobs.py --all-models

    # Submit for a single model
    uv run python training/scripts/submit_grpo_jobs.py --model qwen3-0.6b

    # Dry run (show what would be submitted)
    uv run python training/scripts/submit_grpo_jobs.py --all-models --dry-run

    # Use local prompts (bundled with code upload, skip data asset)
    uv run python training/scripts/submit_grpo_jobs.py \
        --model qwen3-0.6b --prompts-local
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

# Models to run GRPO on — keyed by short name.
GRPO_MODELS: dict[str, dict] = {
    "qwen3-0.6b": {
        "model_id": "unsloth/Qwen3-0.6B-unsloth-bnb-4bit",
        "max_seq_length": 4096,
    },
    "liquid-1.2b": {
        "model_id": "LiquidAI/LFM2.5-1.2B-Instruct",
        "no_4bit": True,
        "target_modules": ("q_proj,k_proj,v_proj,out_proj,in_proj,w1,w2,w3"),
        "max_seq_length": 4096,
    },
}

# Default GRPO training configuration
DEFAULT_CONFIG: dict[str, int | float | str] = {
    "max_seq_length": 4096,
    "batch_size": 1,
    "gradient_accumulation_steps": 4,
    "learning_rate": 5e-6,
    "num_epochs": 1,
    "lora_r": 32,
    "lora_alpha": 32,
    "num_generations": 4,
    "temperature": 0.7,
    "max_new_tokens": 512,
    "beta": 0.01,
    "logging_steps": 1,
    "save_steps": 50,
}

PROMPTS_ASSET_NAME = "pantrypilot-grpo-prompts"


def load_workspace_config() -> tuple[str, str, str]:
    """Load Azure ML workspace config from config.json."""
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

    sub_id, rg, ws = load_workspace_config()
    logger.info(f"Connecting to workspace: {ws}")
    return MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=sub_id,
        resource_group_name=rg,
        workspace_name=ws,
    )


def ensure_prompts_data_asset(
    ml_client: MLClient,
    prompts_path: Path,
) -> str:
    """Upload grpo_prompts.json as an Azure ML Data Asset.

    If the asset already exists, a new version is created.

    Returns:
        Azure ML data asset reference, e.g.
        ``azureml:pantrypilot-grpo-prompts:1``
    """
    from azure.ai.ml.constants import AssetTypes
    from azure.ai.ml.entities import Data

    if not prompts_path.exists():
        logger.error(f"Prompts file not found: {prompts_path}")
        sys.exit(1)

    # Count prompts for metadata
    with open(prompts_path) as f:
        prompts = json.load(f)
    num_prompts = len(prompts)

    # Determine next version
    try:
        existing = list(ml_client.data.list(name=PROMPTS_ASSET_NAME))
        next_version = str(max((int(a.version) for a in existing), default=0) + 1)
    except Exception:
        next_version = "1"

    logger.info(
        f"📦 Uploading {prompts_path.name} as "
        f"{PROMPTS_ASSET_NAME}:{next_version} "
        f"({num_prompts} prompts)"
    )

    data_asset = Data(
        name=PROMPTS_ASSET_NAME,
        version=next_version,
        description=(
            f"GRPO evaluation prompts for PantryPilot "
            f"tool-calling RL ({num_prompts} prompts)"
        ),
        type=AssetTypes.URI_FILE,
        path=str(prompts_path),
        tags={
            "prompts": str(num_prompts),
            "stage": "grpo",
        },
    )

    created = ml_client.data.create_or_update(data_asset)
    ref = f"azureml:{created.name}:{created.version}"
    logger.info(f"✅ Registered data asset: {ref}")
    return ref


def get_latest_prompts_ref(ml_client: MLClient) -> str | None:
    """Get the latest version reference for prompts data asset."""
    try:
        assets = list(ml_client.data.list(name=PROMPTS_ASSET_NAME))
        if not assets:
            return None
        latest = sorted(assets, key=lambda a: int(a.version))[-1]
        return f"azureml:{PROMPTS_ASSET_NAME}:{latest.version}"
    except Exception:
        return None


def submit_grpo_job(
    ml_client: MLClient,
    model_name: str,
    model_cfg: dict,
    config: dict,
    prompts_ref: str | None = None,
    dry_run: bool = False,
) -> str | None:
    """Submit a GRPO training job to Azure ML.

    Args:
        ml_client: Azure ML client
        model_name: Short name (e.g., 'qwen3-0.6b')
        model_cfg: Model-specific configuration
        config: Training configuration
        prompts_ref: Azure ML data asset ref for prompts,
            or None to bundle with code upload
        dry_run: If True, don't actually submit

    Returns:
        Job name if submitted, None if dry run
    """
    from azure.ai.ml import Input, command
    from azure.ai.ml.constants import AssetTypes, InputOutputModes

    model_id = model_cfg["model_id"]
    job_name = f"grpo-{model_name}"

    project_root = Path(__file__).parent.parent.parent.resolve()
    training_dir = project_root / "training"

    # Prompts: data asset input or local file bundled with code
    if prompts_ref:
        prompts_arg = "${inputs.prompts_data}"
    else:
        prompts_arg = "data/grpo_prompts.json"

    # Build command
    cmd = (
        "python scripts/grpo_train.py "
        f"--base_model {model_id} "
        f"--prompts_path {prompts_arg} "
        f"--output_dir ./outputs/{model_name} "
        f"--run_name {job_name} "
        f"--max_seq_length {config['max_seq_length']} "
        f"--batch_size {config['batch_size']} "
        f"--gradient_accumulation_steps "
        f"{config['gradient_accumulation_steps']} "
        f"--learning_rate {config['learning_rate']} "
        f"--num_epochs {config['num_epochs']} "
        f"--lora_r {config['lora_r']} "
        f"--lora_alpha {config['lora_alpha']} "
        f"--num_generations {config['num_generations']} "
        f"--temperature {config['temperature']} "
        f"--max_new_tokens {config['max_new_tokens']} "
        f"--beta {config['beta']} "
        f"--logging_steps {config['logging_steps']} "
        f"--save_steps {config['save_steps']} "
    )

    # Append model-specific flags
    if model_cfg.get("no_4bit"):
        cmd += "--no_4bit "
    if model_cfg.get("target_modules"):
        cmd += f"--target_modules {model_cfg['target_modules']} "
    if model_cfg.get("install_mamba"):
        cmd += "--install_mamba "

    # Build inputs dict
    inputs = {}
    if prompts_ref:
        inputs["prompts_data"] = Input(
            type=AssetTypes.URI_FILE,
            path=prompts_ref,
            mode=InputOutputModes.RO_MOUNT,
        )

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Model: {model_name} ({model_id})")
    logger.info(f"Job:   {job_name}")
    if prompts_ref:
        logger.info(f"Prompts: {prompts_ref}")
    else:
        logger.info("Prompts: bundled with code (local)")
    logger.info(f"Config: {json.dumps(config, indent=2)}")

    if dry_run:
        logger.info("DRY RUN — would submit command:")
        logger.info(cmd)
        return None

    job = command(
        display_name=f"GRPO: {model_name}",
        description=(f"GRPO RL training for {model_id} (tool-calling optimisation)"),
        experiment_name="pantrypilot-grpo",
        code=str(training_dir),
        command=cmd,
        inputs=inputs if inputs else None,
        environment="unsloth-training@latest",
        compute="gpu-cluster",
        instance_count=1,
        tags={
            "model": model_id,
            "stage": "grpo",
            "purpose": "rl-training",
        },
    )

    logger.info("Submitting job...")
    submitted = ml_client.jobs.create_or_update(job)

    logger.info(f"✅ Job submitted: {submitted.name}")
    logger.info(f"   Status: {submitted.status}")
    logger.info(f"   URL: {submitted.studio_url}")

    return submitted.name


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Submit GRPO training jobs to Azure ML"
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=list(GRPO_MODELS.keys()),
        help="Model to train (short name)",
    )
    parser.add_argument(
        "--all-models",
        action="store_true",
        help="Submit jobs for all configured models",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be submitted without submitting",
    )
    parser.add_argument(
        "--prompts-local",
        action="store_true",
        help="Bundle prompts with code upload instead of using a data asset",
    )
    parser.add_argument(
        "--upload-prompts",
        action="store_true",
        help="Force re-upload of prompts as new data asset version",
    )
    parser.add_argument(
        "--num-epochs",
        type=int,
        default=None,
        help="Override number of epochs",
    )
    parser.add_argument(
        "--num-generations",
        type=int,
        default=None,
        help="Override number of generations per prompt",
    )

    args = parser.parse_args()
    if not args.model and not args.all_models:
        parser.error("Specify --model <name> or --all-models")
    return args


def build_config(args: argparse.Namespace) -> dict:
    """Build training config with CLI overrides."""
    config = dict(DEFAULT_CONFIG)
    if args.num_epochs is not None:
        config["num_epochs"] = args.num_epochs
    if args.num_generations is not None:
        config["num_generations"] = args.num_generations
    return config


def resolve_models(args: argparse.Namespace) -> dict[str, dict]:
    """Determine which models to submit."""
    if args.all_models:
        return {k: dict(v) for k, v in GRPO_MODELS.items()}
    return {args.model: dict(GRPO_MODELS[args.model])}


def resolve_prompts(
    ml_client: MLClient,
    args: argparse.Namespace,
) -> str | None:
    """Resolve prompts data asset reference.

    Returns None when --prompts-local is set (bundled with code).
    Otherwise uploads or reuses existing data asset.
    """
    if args.prompts_local:
        return None

    project_root = Path(__file__).parent.parent.parent.resolve()
    prompts_path = project_root / "training" / "data" / "grpo_prompts.json"

    # Upload new version if explicitly requested
    if args.upload_prompts:
        return ensure_prompts_data_asset(ml_client, prompts_path)

    # Try to reuse existing asset
    ref = get_latest_prompts_ref(ml_client)
    if ref:
        logger.info(f"Using existing prompts asset: {ref}")
        return ref

    # No existing asset — upload for the first time
    logger.info("No prompts data asset found, uploading...")
    return ensure_prompts_data_asset(ml_client, prompts_path)


def main() -> int:
    """Main entry point."""
    args = parse_args()
    config = build_config(args)
    ml_client = create_ml_client()
    models_to_run = resolve_models(args)
    prompts_ref = resolve_prompts(ml_client, args)

    # Submit jobs
    submitted: list[str] = []
    for model_name, model_cfg in models_to_run.items():
        # Merge per-model config overrides
        job_config = dict(config)
        for key in (
            "max_seq_length",
            "lora_r",
            "lora_alpha",
            "learning_rate",
        ):
            if key in model_cfg:
                job_config[key] = model_cfg[key]

        try:
            job_name = submit_grpo_job(
                ml_client,
                model_name,
                model_cfg,
                job_config,
                prompts_ref=prompts_ref,
                dry_run=args.dry_run,
            )
            if job_name:
                submitted.append(job_name)
        except Exception as e:
            logger.error(f"Failed for {model_name}: {e}")
            continue

    # Summary
    print(f"\n{'=' * 60}")
    if args.dry_run:
        print(f"DRY RUN: Would have submitted {len(models_to_run)} jobs")
    else:
        print(f"Submitted {len(submitted)} jobs:")
        for name in submitted:
            print(f"  - {name}")
        print("\nMonitor jobs in Azure ML Studio or with:")
        print("  az ml job show --name <job-name>")

    return 0


if __name__ == "__main__":
    sys.exit(main())
