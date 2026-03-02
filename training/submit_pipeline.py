#!/usr/bin/env python3
"""
PantryPilot Training Pipeline — Submission CLI

Submits an Azure ML training pipeline (DAPT → SFT → GRPO) using a JSON
configuration file.  Supports CLI overrides for model selection, stage
enablement, compute target, and a dry-run mode that validates the pipeline
without submitting.

Usage:
    # SFT-only from config file
    python training/submit_pipeline.py --config training/configs/sft_only.json

    # Full pipeline with overrides
    python training/submit_pipeline.py \\
        --config training/configs/full_pipeline.json \\
        --base-model unsloth/Qwen3-0.6B-unsloth-bnb-4bit

    # Dry-run validation
    python training/submit_pipeline.py \\
        --config training/configs/sft_only.json --dry-run

    # Inline (no config file) — minimal SFT run
    python training/submit_pipeline.py \\
        --base-model unsloth/Qwen3-0.6B-unsloth-bnb-4bit \\
        --sft-data azureml:pantrypilot-sft-data:1

References:
    - training/pipeline.py          — Pipeline builder
    - training/configs/             — Preset configurations
    - training/components/          — Component YAML specs
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Add parent to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent))

from pipeline import build_training_pipeline, create_ml_client, load_pipeline_config

logger = logging.getLogger(__name__)


def _merge_cli_overrides(config: dict[str, Any], args: argparse.Namespace) -> None:
    """Apply CLI argument overrides onto the config dict (in-place)."""
    if args.base_model:
        config["base_model"] = args.base_model
    if args.compute:
        config["compute"] = args.compute
    if args.sft_data:
        config["sft_data"] = args.sft_data
    if args.val_data:
        config["val_data"] = args.val_data
    if args.dapt_data:
        config["dapt_data"] = args.dapt_data
    if args.grpo_prompts:
        config["grpo_prompts"] = args.grpo_prompts

    # Stage toggles — only override if explicitly passed
    if args.enable_dapt:
        config["enable_dapt"] = True
    if args.disable_dapt:
        config["enable_dapt"] = False
    if args.enable_grpo:
        config["enable_grpo"] = True
    if args.disable_grpo:
        config["enable_grpo"] = False


def _print_config_summary(config: dict[str, Any]) -> None:
    """Print a human-readable configuration summary."""
    stages = []
    if config.get("enable_dapt"):
        stages.append("DAPT")
    stages.append("SFT")
    if config.get("enable_grpo"):
        stages.append("GRPO")

    print()
    print("Pipeline Configuration")
    print("=" * 60)
    print(f"  Model:    {config.get('base_model', '(not set)')}")
    print(f"  Stages:   {' → '.join(stages)}")
    print(f"  Compute:  {config.get('compute', 'gpu-cluster')}")
    print()
    print("  Data:")
    if config.get("enable_dapt"):
        print(f"    DAPT:     {config.get('dapt_data', '(not set)')}")
    print(f"    SFT:      {config.get('sft_data', '(not set)')}")
    if config.get("val_data"):
        print(f"    Val:      {config['val_data']}")
    if config.get("enable_grpo"):
        print(f"    GRPO:     {config.get('grpo_prompts', '(not set)')}")

    # Stage hyperparameters
    for stage_name in ("dapt", "sft", "grpo"):
        params = config.get(stage_name, {})
        if params:
            print()
            print(f"  {stage_name.upper()} hyperparameters:")
            for k, v in sorted(params.items()):
                print(f"    {k}: {v}")

    print()


def main() -> int:
    """CLI entry point for pipeline submission."""
    parser = argparse.ArgumentParser(
        description="Submit a PantryPilot training pipeline to Azure ML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --config training/configs/sft_only.json\n"
            "  %(prog)s --config training/configs/full_pipeline.json --dry-run\n"
            "  %(prog)s --base-model unsloth/Qwen3-0.6B-unsloth-bnb-4bit "
            "--sft-data azureml:pantrypilot-sft-data:1\n"
        ),
    )

    # Configuration
    parser.add_argument(
        "--config",
        type=str,
        help="JSON configuration file path (see training/configs/)",
    )

    # Model and compute overrides
    parser.add_argument(
        "--base-model",
        type=str,
        help="HuggingFace model ID (overrides config file)",
    )
    parser.add_argument(
        "--compute",
        type=str,
        help="Azure ML compute target (default: gpu-cluster)",
    )

    # Data path overrides
    parser.add_argument("--sft-data", type=str, help="SFT training data path")
    parser.add_argument("--val-data", type=str, help="SFT validation data path")
    parser.add_argument("--dapt-data", type=str, help="DAPT corpus data path")
    parser.add_argument("--grpo-prompts", type=str, help="GRPO prompts data path")

    # Stage toggles
    parser.add_argument(
        "--enable-dapt",
        action="store_true",
        default=False,
        help="Enable DAPT stage",
    )
    parser.add_argument(
        "--disable-dapt",
        action="store_true",
        default=False,
        help="Disable DAPT stage (overrides config)",
    )
    parser.add_argument(
        "--enable-grpo",
        action="store_true",
        default=False,
        help="Enable GRPO stage",
    )
    parser.add_argument(
        "--disable-grpo",
        action="store_true",
        default=False,
        help="Disable GRPO stage (overrides config)",
    )

    # Execution control
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate pipeline configuration without submitting",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Build configuration
    if args.config:
        try:
            config = load_pipeline_config(args.config)
            logger.info(f"Loaded config from {args.config}")
        except (FileNotFoundError, ValueError) as e:
            logger.error(str(e))
            return 1
    else:
        # Build config from CLI arguments only
        config = {}

    _merge_cli_overrides(config, args)

    # Validate minimum required config
    if "base_model" not in config:
        logger.error("No base_model specified. Provide --config or --base-model.")
        return 1
    if "sft_data" not in config:
        logger.error(
            "No sft_data specified. Provide --config with sft_data or --sft-data."
        )
        return 1

    _print_config_summary(config)

    # Build pipeline
    try:
        pipeline_job = build_training_pipeline(config)
        logger.info("Pipeline built successfully")
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Pipeline build failed: {e}")
        return 1

    if args.dry_run:
        print("Dry-run mode — pipeline validated but NOT submitted.")
        print()
        # Print the resolved pipeline structure
        stages = []
        if config.get("enable_dapt"):
            stages.append("DAPT")
        stages.append("SFT")
        if config.get("enable_grpo"):
            stages.append("GRPO")
        print(f"  Pipeline: {' → '.join(stages)}")
        print(f"  Experiment: {pipeline_job.experiment_name}")
        print(f"  Tags: {json.dumps(dict(pipeline_job.tags), indent=2)}")
        return 0

    # Submit to Azure ML
    try:
        ml_client = create_ml_client()
        returned_job = ml_client.jobs.create_or_update(pipeline_job)
        print()
        print("Pipeline submitted successfully!")
        print(f"  Job name: {returned_job.name}")
        print(f"  Studio URL: {returned_job.studio_url}")
        print()
        return 0
    except Exception as e:
        logger.error(f"Pipeline submission failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
