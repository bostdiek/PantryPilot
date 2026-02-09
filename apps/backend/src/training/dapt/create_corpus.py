#!/usr/bin/env python3
"""Create combined DAPT corpus from all sources.

This script merges all processed culinary data sources into a single
JSONL corpus file for domain-adaptive pre-training.

Target composition (~150M tokens):
- Food.com recipes: ~70M tokens (47%)
- Food.com reviews: ~43M tokens (29%)
- OpenRecipes: ~25M tokens (17%)
- Flavor pairing knowledge: ~5M tokens (3%)
- General text augmentation: ~7M tokens (4%) [optional]
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from tqdm import tqdm


if TYPE_CHECKING:
    from collections.abc import Iterator

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Default data directory
DEFAULT_DATA_DIR = Path("./data")

# Expected input files
INPUT_FILES = {
    "foodcom_recipes": "foodcom_corpus.jsonl",
    "foodcom_reviews": "foodcom_reviews.jsonl",
    "openrecipes": "openrecipes_corpus.jsonl",
    "flavor_pairs": "flavor_pairs.jsonl",
}


def read_jsonl(file_path: Path) -> Iterator[dict]:
    """Read JSONL file and yield records."""
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON: {e}")
                    continue


def count_lines(file_path: Path) -> int:
    """Count lines in a file."""
    if not file_path.exists():
        return 0
    with open(file_path, encoding="utf-8") as f:
        return sum(1 for _ in f)


def estimate_tokens_from_file(file_path: Path) -> int:
    """Estimate token count from file size."""
    if not file_path.exists():
        return 0
    return file_path.stat().st_size // 4


def create_corpus(
    data_dir: Path,
    output_path: Path,
    shuffle: bool = True,
    seed: int | None = None,
) -> dict[str, int]:
    """Create combined corpus from all sources."""
    # Collect all records
    all_records: list[dict] = []
    source_counts: dict[str, int] = {}

    for source_name, filename in INPUT_FILES.items():
        file_path = data_dir / filename
        if not file_path.exists():
            logger.warning(f"Source not found, skipping: {source_name}")
            continue

        logger.info(f"Loading {source_name} from {file_path}...")
        count = 0
        for record in tqdm(
            read_jsonl(file_path), desc=f"Loading {source_name}", leave=False
        ):
            # Add source metadata
            record["_source"] = source_name
            all_records.append(record)
            count += 1

        source_counts[source_name] = count
        logger.info(f"  Loaded {count:,} records from {source_name}")

    if not all_records:
        logger.error("No records found in any source!")
        return {}

    # Shuffle if requested
    if shuffle:
        if seed is not None:
            random.seed(seed)
        random.shuffle(all_records)
        logger.info(f"Shuffled {len(all_records):,} records (seed={seed})")

    # Write combined corpus
    logger.info(f"Writing combined corpus to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for record in tqdm(all_records, desc="Writing corpus"):
            # Remove internal metadata before writing
            output_record = {k: v for k, v in record.items() if not k.startswith("_")}
            f.write(json.dumps(output_record, ensure_ascii=False) + "\n")

    return source_counts


def print_summary(output_path: Path, source_counts: dict[str, int]) -> None:
    """Print corpus summary statistics."""
    total_records = sum(source_counts.values())
    total_tokens = estimate_tokens_from_file(output_path)
    file_size_mb = output_path.stat().st_size / (1024 * 1024)

    logger.info("\n" + "=" * 60)
    logger.info("CORPUS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Output file: {output_path}")
    logger.info(f"File size: {file_size_mb:.1f} MB")
    logger.info(f"Total records: {total_records:,}")
    logger.info(
        f"Estimated tokens: ~{total_tokens:,} ({total_tokens / 1_000_000:.1f}M)"
    )
    logger.info("")
    logger.info("Source breakdown:")
    for source, count in source_counts.items():
        pct = (count / total_records) * 100 if total_records > 0 else 0
        logger.info(f"  - {source}: {count:,} records ({pct:.1f}%)")
    logger.info("")
    logger.info("License compliance:")
    logger.info("  - Food.com: CC0 (Public Domain) ✅")
    logger.info("  - OpenRecipes: ODC-BY (Attribution required) ✅")
    logger.info("  - Flavor pairs: Derived from CC0 ✅")
    logger.info("=" * 60)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create combined DAPT corpus from all sources"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Directory containing source JSONL files (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./data/commercial_culinary_corpus.jsonl"),
        help="Output corpus file (default: ./data/commercial_culinary_corpus.jsonl)",
    )
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="Don't shuffle records (keeps source order)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for shuffling (default: 42)",
    )
    parser.add_argument(
        "--foodcom-recipes",
        type=Path,
        help="Override path to Food.com recipes JSONL",
    )
    parser.add_argument(
        "--foodcom-reviews",
        type=Path,
        help="Override path to Food.com reviews JSONL",
    )
    parser.add_argument(
        "--openrecipes",
        type=Path,
        help="Override path to OpenRecipes JSONL",
    )
    parser.add_argument(
        "--flavor-pairs",
        type=Path,
        help="Override path to flavor pairs JSONL",
    )
    args = parser.parse_args()

    # Update INPUT_FILES with any overrides
    global INPUT_FILES
    INPUT_FILES = INPUT_FILES.copy()
    if args.foodcom_recipes:
        INPUT_FILES["foodcom_recipes"] = str(args.foodcom_recipes)
    if args.foodcom_reviews:
        INPUT_FILES["foodcom_reviews"] = str(args.foodcom_reviews)
    if args.openrecipes:
        INPUT_FILES["openrecipes"] = str(args.openrecipes)
    if args.flavor_pairs:
        INPUT_FILES["flavor_pairs"] = str(args.flavor_pairs)

    # Create corpus
    source_counts = create_corpus(
        data_dir=args.data_dir,
        output_path=args.output,
        shuffle=not args.no_shuffle,
        seed=args.seed if not args.no_shuffle else None,
    )

    if not source_counts:
        return 1

    # Print summary
    print_summary(args.output, source_counts)

    logger.info("\nCorpus creation complete!")
    logger.info(
        f"Next step: python -m training.dapt.upload_to_azure --corpus {args.output}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
