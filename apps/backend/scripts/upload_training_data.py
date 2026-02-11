#!/usr/bin/env python3
"""Upload SFT training data to Azure ML workspace as Data Assets.

This script uploads exported training/validation data to Azure Blob Storage
and registers them as Data Assets in the Azure ML workspace.

Prerequisites:
    1. Azure CLI logged in: `az login`
    2. Azure ML extension: `az extension add -n ml`
    3. Install dependencies: `uv sync --group training`
    4. Export training data first using export_training_data.py

Usage:
    # Upload with default settings (expects train.jsonl and val.jsonl in data/)
    uv run python scripts/upload_training_data.py

    # Specify custom paths
    uv run python scripts/upload_training_data.py \\
        --train-file data/custom_train.jsonl \\
        --val-file data/custom_val.jsonl

    # Specify workspace directly
    uv run python scripts/upload_training_data.py \\
        --subscription-id <sub-id> \\
        --resource-group rg-pantrypilot-dev \\
        --workspace-name pp-aml-dev

    # Custom version number
    uv run python scripts/upload_training_data.py --version 2
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from azure.ai.ml import MLClient


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Default values
DEFAULT_TRAIN_FILE = Path("./data/train.jsonl")
DEFAULT_VAL_FILE = Path("./data/val.jsonl")
DEFAULT_TRAIN_ASSET_NAME = "pantrypilot-sft-data"
DEFAULT_VAL_ASSET_NAME = "pantrypilot-sft-data-val"
DEFAULT_VERSION = "1"


def get_ml_client(
    subscription_id: str | None = None,
    resource_group: str | None = None,
    workspace_name: str | None = None,
) -> MLClient:
    """Get Azure ML client with authentication."""
    try:
        from azure.ai.ml import MLClient
        from azure.identity import DefaultAzureCredential
    except ImportError as e:
        logger.error(
            "Azure ML SDK not installed. Install with:\n"
            "  uv sync --group training\n"
            "Or add manually: uv add --group training azure-ai-ml azure-identity"
        )
        raise SystemExit(1) from e

    credential = DefaultAzureCredential()

    # If workspace details provided, connect to specific workspace
    if subscription_id and resource_group and workspace_name:
        return MLClient(
            credential=credential,
            subscription_id=subscription_id,
            resource_group_name=resource_group,
            workspace_name=workspace_name,
        )

    # Try to get workspace from config file
    try:
        return MLClient.from_config(credential=credential)
    except Exception:
        logger.error(
            "Could not connect to Azure ML workspace.\n"
            "Either provide --subscription-id, --resource-group, --workspace-name\n"
            "or create a config.json file in your working directory."
        )
        raise


def upload_data_asset(
    ml_client: MLClient,
    file_path: Path,
    asset_name: str,
    asset_version: str,
    description: str,
    tags: dict[str, str],
) -> str:
    """Upload file and register as Data Asset.

    Args:
        ml_client: Azure ML client
        file_path: Path to JSONL file to upload
        asset_name: Name for the Data Asset
        asset_version: Version string
        description: Human-readable description
        tags: Metadata tags for the asset

    Returns:
        Asset path in Azure Blob Storage
    """
    from azure.ai.ml.constants import AssetTypes
    from azure.ai.ml.entities import Data

    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    line_count = sum(1 for _ in file_path.open())

    logger.info(f"Uploading {file_path} ({file_size_mb:.2f} MB, {line_count} samples)")

    # Create data asset definition
    data_asset = Data(
        name=asset_name,
        version=asset_version,
        description=description,
        type=AssetTypes.URI_FILE,
        path=str(file_path),
        tags={**tags, "samples": str(line_count)},
    )

    # Create/update the data asset (uploads file to blob storage)
    logger.info(f"Registering as Data Asset: {asset_name}:{asset_version}")
    created_asset = ml_client.data.create_or_update(data_asset)

    registered_name = f"{created_asset.name}:{created_asset.version}"
    logger.info(f"Successfully registered: {registered_name}")
    logger.info(f"Asset path: {created_asset.path}")

    return str(created_asset.path)


def main() -> int:
    """Main entry point for upload script."""
    parser = argparse.ArgumentParser(
        description="Upload SFT training data to Azure ML as Data Assets"
    )
    parser.add_argument(
        "--train-file",
        type=Path,
        default=DEFAULT_TRAIN_FILE,
        help=f"Path to training data JSONL (default: {DEFAULT_TRAIN_FILE})",
    )
    parser.add_argument(
        "--val-file",
        type=Path,
        default=DEFAULT_VAL_FILE,
        help=f"Path to validation data JSONL (default: {DEFAULT_VAL_FILE})",
    )
    parser.add_argument(
        "--train-asset-name",
        default=DEFAULT_TRAIN_ASSET_NAME,
        help=f"Name for training Data Asset (default: {DEFAULT_TRAIN_ASSET_NAME})",
    )
    parser.add_argument(
        "--val-asset-name",
        default=DEFAULT_VAL_ASSET_NAME,
        help=f"Name for validation Data Asset (default: {DEFAULT_VAL_ASSET_NAME})",
    )
    parser.add_argument(
        "--version",
        default=DEFAULT_VERSION,
        help=f"Version for both Data Assets (default: {DEFAULT_VERSION})",
    )
    parser.add_argument(
        "--subscription-id",
        help="Azure subscription ID",
    )
    parser.add_argument(
        "--resource-group",
        help="Azure resource group name",
    )
    parser.add_argument(
        "--workspace-name",
        help="Azure ML workspace name",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip uploading validation data",
    )

    args = parser.parse_args()

    # Check files exist before connecting
    if not args.train_file.exists():
        logger.error(f"Training file not found: {args.train_file}")
        logger.info("Run export_training_data.py first to generate training data.")
        return 1

    if not args.skip_validation and not args.val_file.exists():
        logger.error(f"Validation file not found: {args.val_file}")
        logger.info(
            "Run export_training_data.py with --val-output to generate validation data."
        )
        return 1

    # Connect to Azure ML
    logger.info("Connecting to Azure ML workspace...")
    ml_client = get_ml_client(
        subscription_id=args.subscription_id,
        resource_group=args.resource_group,
        workspace_name=args.workspace_name,
    )
    logger.info(f"Connected to workspace: {ml_client.workspace_name}")

    # Common tags
    base_tags = {
        "format": "chatml-jsonl",
        "use": "sft",
        "source": "pantrypilot-conversations",
    }

    # Upload training data
    upload_data_asset(
        ml_client=ml_client,
        file_path=args.train_file,
        asset_name=args.train_asset_name,
        asset_version=args.version,
        description=(
            "PantryPilot SFT training data in ChatML JSONL format. "
            "Contains AI assistant conversations with tool calls for "
            "recipe search, meal planning, and web fetching."
        ),
        tags={**base_tags, "split": "train"},
    )

    val_path = None
    if not args.skip_validation:
        val_path = upload_data_asset(
            ml_client=ml_client,
            file_path=args.val_file,
            asset_name=args.val_asset_name,
            asset_version=args.version,
            description=(
                "PantryPilot SFT validation data in ChatML JSONL format. "
                "Used for evaluating model performance during fine-tuning."
            ),
            tags={**base_tags, "split": "validation"},
        )

    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info("Upload complete!")
    logger.info(f"  Training asset: {args.train_asset_name}:{args.version}")
    if val_path:
        logger.info(f"  Validation asset: {args.val_asset_name}:{args.version}")
    logger.info("")
    logger.info("Use in training scripts:")
    train_get = f'ml_client.data.get("{args.train_asset_name}", "{args.version}")'
    logger.info(f"  train_data = {train_get}")
    if val_path:
        val_get = f'ml_client.data.get("{args.val_asset_name}", "{args.version}")'
        logger.info(f"  val_data = {val_get}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
