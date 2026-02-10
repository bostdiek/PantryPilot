#!/usr/bin/env python3
"""Process Food.com dataset for domain-adaptive pre-training.

This script converts the raw Food.com CSV files into JSONL format suitable
for language model pre-training.

The Food.com dataset is licensed under CC0 (Public Domain) and is free for
commercial use.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from ast import literal_eval
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from tqdm import tqdm


if TYPE_CHECKING:
    from collections.abc import Iterator

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Minimum review length to include
MIN_REVIEW_LENGTH = 50

# Regex patterns for identifying substitution tips in reviews
SUBSTITUTION_PATTERNS = r"substitut|instead of|replaced|used .* instead|swap"


def safe_literal_eval(value: str) -> list[str]:
    """Safely evaluate a string representation of a list."""
    if pd.isna(value):
        return []
    try:
        result = literal_eval(value)
        return result if isinstance(result, list) else []
    except (ValueError, SyntaxError):
        return []


def format_recipe(row: pd.Series) -> str:
    """Format a recipe row into training text."""
    name = str(row["name"]).strip()
    ingredients = row["ingredients"]
    steps = row["steps"]
    tags = row["tags"]
    minutes = row.get("minutes", 0)
    description = row.get("description", "")

    # Format ingredients
    ingredients_str = ", ".join(ingredients) if ingredients else "Not specified"

    # Format steps
    if steps:
        steps_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(steps))
    else:
        steps_str = "Not specified"

    # Format tags (take first 5)
    tags_str = ", ".join(tags[:5]) if tags else "general"

    # Build recipe text in markdown-like format
    text = f"""# {name}

Category: {tags_str}
Prep Time: {minutes} minutes

## Ingredients
{ingredients_str}

## Instructions
{steps_str}
"""

    # Add description if available and meaningful
    if description and isinstance(description, str) and len(description) > 10:
        text += f"\n## About\n{description.strip()}\n"

    return text


def process_recipes(input_dir: Path) -> Iterator[dict[str, str]]:
    """Process recipes from CSV and yield JSONL records."""
    recipes_path = input_dir / "RAW_recipes.csv"

    if not recipes_path.exists():
        logger.error(f"Recipes file not found: {recipes_path}")
        return

    logger.info(f"Loading recipes from {recipes_path}...")
    recipes = pd.read_csv(recipes_path)
    logger.info(f"Loaded {len(recipes):,} recipes")

    # Parse list columns
    recipes["steps"] = recipes["steps"].apply(safe_literal_eval)
    recipes["ingredients"] = recipes["ingredients"].apply(safe_literal_eval)
    recipes["tags"] = recipes["tags"].apply(safe_literal_eval)

    for _, row in tqdm(
        recipes.iterrows(), total=len(recipes), desc="Processing recipes"
    ):
        text = format_recipe(row)
        yield {"text": text}


def process_reviews(input_dir: Path) -> Iterator[dict[str, str]]:
    """Process reviews with substitution tips."""
    reviews_path = input_dir / "RAW_interactions.csv"

    if not reviews_path.exists():
        logger.warning(f"Reviews file not found: {reviews_path}, skipping")
        return

    logger.info(f"Loading reviews from {reviews_path}...")
    reviews = pd.read_csv(reviews_path)
    logger.info(f"Loaded {len(reviews):,} reviews")

    # Filter for reviews with substitution information
    mask = reviews["review"].str.contains(SUBSTITUTION_PATTERNS, case=False, na=False)
    substitution_reviews = reviews[mask]
    logger.info(f"Found {len(substitution_reviews):,} reviews with substitution tips")

    for _, row in tqdm(
        substitution_reviews.iterrows(),
        total=len(substitution_reviews),
        desc="Processing reviews",
    ):
        review = row.get("review", "")
        if pd.isna(review) or len(str(review)) < MIN_REVIEW_LENGTH:
            continue

        text = f"Cook's Tip: {str(review).strip()}"
        yield {"text": text}


def write_jsonl(records: Iterator[dict[str, str]], output_path: Path) -> int:
    """Write records to JSONL file and return count."""
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def estimate_tokens(file_path: Path) -> int:
    """Estimate token count using 4 chars per token heuristic."""
    if not file_path.exists():
        return 0
    file_size = file_path.stat().st_size
    # Rough estimate: 4 chars per token for English text
    return file_size // 4


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process Food.com dataset for pre-training"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing RAW_recipes.csv and RAW_interactions.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./data/foodcom_corpus.jsonl"),
        help="Output JSONL file for recipes (default: ./data/foodcom_corpus.jsonl)",
    )
    parser.add_argument(
        "--reviews-output",
        type=Path,
        default=None,
        help="Output JSONL file for reviews (default: same dir as --output)",
    )
    parser.add_argument(
        "--no-reviews",
        action="store_true",
        help="Skip processing reviews",
    )
    args = parser.parse_args()

    # Set default reviews output
    if args.reviews_output is None:
        args.reviews_output = args.output.parent / "foodcom_reviews.jsonl"

    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Process recipes
    recipe_count = write_jsonl(process_recipes(args.input_dir), args.output)
    logger.info(f"Wrote {recipe_count:,} recipes to {args.output}")
    recipe_tokens = estimate_tokens(args.output)
    logger.info(
        f"Estimated ~{recipe_tokens:,} tokens ({recipe_tokens / 1_000_000:.1f}M)"
    )

    # Process reviews
    if not args.no_reviews:
        review_count = write_jsonl(process_reviews(args.input_dir), args.reviews_output)
        logger.info(f"Wrote {review_count:,} reviews to {args.reviews_output}")
        review_tokens = estimate_tokens(args.reviews_output)
        token_m = review_tokens / 1_000_000
        logger.info(f"Estimated ~{review_tokens:,} tokens ({token_m:.1f}M)")
    else:
        review_tokens = 0

    total_tokens = recipe_tokens + review_tokens
    total_m = total_tokens / 1_000_000
    logger.info(f"\nTotal estimated tokens: ~{total_tokens:,} ({total_m:.1f}M)")
    logger.info("\nProcessing complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
