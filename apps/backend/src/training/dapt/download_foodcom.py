#!/usr/bin/env python3
"""Download Food.com dataset from Kaggle.

This script downloads the Food.com Recipes and Interactions dataset (CC0 license)
from Kaggle for use in domain-adaptive pre-training.

Prerequisites:
    1. Install dependencies: uv sync --group dapt
    2. Configure Kaggle API key at ~/.kaggle/kaggle.json
       See: https://www.kaggle.com/docs/api#authentication
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import zipfile
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

KAGGLE_DATASET = "shuyangli94/food-com-recipes-and-user-interactions"
EXPECTED_FILES = ["RAW_recipes.csv", "RAW_interactions.csv"]


def check_kaggle_credentials() -> bool:
    """Check if Kaggle API credentials are configured."""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        logger.error(
            "Kaggle credentials not found at ~/.kaggle/kaggle.json\n"
            "Please configure your Kaggle API key:\n"
            "  1. Go to https://www.kaggle.com/settings\n"
            "  2. Click 'Create New Token' under API section\n"
            "  3. Move downloaded kaggle.json to ~/.kaggle/\n"
            "  4. Run: chmod 600 ~/.kaggle/kaggle.json"
        )
        return False
    return True


def download_dataset(output_dir: Path) -> bool:
    """Download the Food.com dataset from Kaggle."""
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading {KAGGLE_DATASET}...")

    try:
        result = subprocess.run(
            [
                "kaggle",
                "datasets",
                "download",
                "-d",
                KAGGLE_DATASET,
                "-p",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Download failed: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("Kaggle CLI not found. Install with: pip install kaggle")
        return False

    return True


def extract_dataset(output_dir: Path) -> bool:
    """Extract the downloaded zip file."""
    zip_path = output_dir / "food-com-recipes-and-user-interactions.zip"

    if not zip_path.exists():
        logger.error(f"Zip file not found: {zip_path}")
        return False

    logger.info("Extracting dataset...")
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(output_dir)
        logger.info(f"Extracted to {output_dir}")

        # Clean up zip file
        zip_path.unlink()
        logger.info("Removed zip file")
    except zipfile.BadZipFile:
        logger.error("Invalid zip file")
        return False

    return True


def verify_files(output_dir: Path) -> bool:
    """Verify that expected files are present."""
    missing = []
    for filename in EXPECTED_FILES:
        if not (output_dir / filename).exists():
            missing.append(filename)

    if missing:
        logger.error(f"Missing expected files: {missing}")
        return False

    logger.info("All expected files present:")
    for filename in EXPECTED_FILES:
        file_path = output_dir / filename
        size_mb = file_path.stat().st_size / (1024 * 1024)
        logger.info(f"  - {filename}: {size_mb:.1f} MB")

    return True


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download Food.com dataset from Kaggle"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./data/foodcom"),
        help="Directory to save downloaded data (default: ./data/foodcom)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download, only extract existing zip",
    )
    args = parser.parse_args()

    # Check if already downloaded
    if all((args.output_dir / f).exists() for f in EXPECTED_FILES):
        logger.info("Dataset already downloaded and extracted")
        return 0

    if not args.skip_download:
        if not check_kaggle_credentials():
            return 1

        if not download_dataset(args.output_dir):
            return 1

    if not extract_dataset(args.output_dir):
        return 1

    if not verify_files(args.output_dir):
        return 1

    logger.info("Download complete!")
    logger.info(
        "Next step: python -m training.dapt.process_foodcom "
        f"--input-dir {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
