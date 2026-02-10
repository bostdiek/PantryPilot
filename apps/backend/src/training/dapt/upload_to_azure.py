#!/usr/bin/env python3
"""Upload DAPT corpus to Azure ML workspace as a Data Asset.

This script uploads the combined DAPT corpus to Azure Blob Storage
and registers it as a Data Asset in Azure ML workspace.

Prerequisites:
    1. Azure CLI logged in: `az login`
    2. Azure ML extension: `az extension add -n ml`
    3. Install dependencies: `uv sync --group dapt`
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
DEFAULT_CORPUS_PATH = Path("./data/commercial_culinary_corpus.jsonl")
DEFAULT_ASSET_NAME = "dapt-culinary-corpus"
DEFAULT_ASSET_VERSION = "1"


def get_ml_client(
    subscription_id: str | None = None,
    resource_group: str | None = None,
    workspace_name: str | None = None,
) -> MLClient:
    """Get Azure ML client with authentication."""
    try:
        from azure.ai.ml import MLClient
        from azure.identity import DefaultAzureCredential
    except ImportError:
        logger.error(
            "Azure ML SDK not installed. Install with:\n"
            "  uv sync --group dapt\n"
            "Or add manually: uv add --group dapt azure-ai-ml azure-identity"
        )
        raise

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


def upload_corpus(
    ml_client: MLClient,
    corpus_path: Path,
    asset_name: str,
    asset_version: str,
    description: str | None = None,
) -> str:
    """Upload corpus file and register as Data Asset."""
    from azure.ai.ml.constants import AssetTypes
    from azure.ai.ml.entities import Data

    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus file not found: {corpus_path}")

    file_size_mb = corpus_path.stat().st_size / (1024 * 1024)
    logger.info(f"Uploading {corpus_path} ({file_size_mb:.1f} MB)...")

    # Create data asset definition
    data_asset = Data(
        name=asset_name,
        version=asset_version,
        description=description
        or (
            "Commercial-use culinary DAPT corpus (~150M tokens) from "
            "Food.com (CC0) and OpenRecipes (ODC-BY)"
        ),
        type=AssetTypes.URI_FILE,
        path=str(corpus_path),
        tags={
            "source": "food.com,openrecipes",
            "license": "CC0,ODC-BY",
            "tokens": "~150M",
            "format": "jsonl",
            "use": "dapt",
        },
    )

    # Create/update the data asset (uploads file to blob storage)
    logger.info(f"Registering as Data Asset: {asset_name}:{asset_version}")
    created_asset = ml_client.data.create_or_update(data_asset)

    registered = f"{created_asset.name}:{created_asset.version}"
    logger.info(f"Successfully registered: {registered}")
    logger.info(f"Asset path: {created_asset.path}")

    return str(created_asset.path)


def verify_upload(ml_client: MLClient, asset_name: str, asset_version: str) -> bool:
    """Verify the data asset exists and is accessible."""
    try:
        asset = ml_client.data.get(name=asset_name, version=asset_version)
        logger.info(f"Verified asset exists: {asset.name}:{asset.version}")
        logger.info(f"  Path: {asset.path}")
        logger.info(f"  Tags: {asset.tags}")
        return True
    except Exception as e:
        logger.error(f"Could not verify asset: {e}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload DAPT corpus to Azure ML workspace"
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS_PATH,
        help=f"Path to corpus JSONL file (default: {DEFAULT_CORPUS_PATH})",
    )
    parser.add_argument(
        "--asset-name",
        default=DEFAULT_ASSET_NAME,
        help=f"Data Asset name (default: {DEFAULT_ASSET_NAME})",
    )
    parser.add_argument(
        "--asset-version",
        default=DEFAULT_ASSET_VERSION,
        help=f"Data Asset version (default: {DEFAULT_ASSET_VERSION})",
    )
    parser.add_argument(
        "--workspace-name",
        help="Azure ML workspace name",
    )
    parser.add_argument(
        "--resource-group",
        help="Azure resource group name",
    )
    parser.add_argument(
        "--subscription-id",
        help="Azure subscription ID",
    )
    parser.add_argument(
        "--description",
        help="Asset description (optional)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing asset, don't upload",
    )
    args = parser.parse_args()

    # Check corpus exists
    if not args.verify_only and not args.corpus.exists():
        logger.error(f"Corpus file not found: {args.corpus}")
        logger.error(
            "Run the corpus creation pipeline first:\n"
            "  python -m training.dapt.download_foodcom --output-dir ./data/foodcom\n"
            "  python -m training.dapt.process_foodcom --input-dir ./data/foodcom\n"
            "  python -m training.dapt.process_openrecipes\n"
            "  python -m training.dapt.extract_flavor_pairs --input ./data/foodcom\n"
            "  python -m training.dapt.create_corpus"
        )
        return 1

    try:
        ml_client = get_ml_client(
            subscription_id=args.subscription_id,
            resource_group=args.resource_group,
            workspace_name=args.workspace_name,
        )
    except Exception as e:
        logger.error(f"Failed to connect to Azure ML: {e}")
        return 1

    if args.verify_only:
        success = verify_upload(ml_client, args.asset_name, args.asset_version)
        return 0 if success else 1

    try:
        asset_path = upload_corpus(
            ml_client=ml_client,
            corpus_path=args.corpus,
            asset_name=args.asset_name,
            asset_version=args.asset_version,
            description=args.description,
        )

        # Verify upload
        if verify_upload(ml_client, args.asset_name, args.asset_version):
            logger.info("\n" + "=" * 60)
            logger.info("UPLOAD COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Asset: {args.asset_name}:{args.asset_version}")
            logger.info(f"Path: {asset_path}")
            logger.info("")
            logger.info("Use in pipeline:")
            logger.info(
                f'  dapt_data = ml_client.data.get("{args.asset_name}", '
                f'version="{args.asset_version}")'
            )
            logger.info("=" * 60)
            return 0
        else:
            return 1

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
