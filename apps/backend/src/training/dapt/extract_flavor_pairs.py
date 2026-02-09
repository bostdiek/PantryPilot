#!/usr/bin/env python3
"""Extract ingredient co-occurrence knowledge from Food.com.

This script analyzes ingredient co-occurrence patterns from the Food.com
dataset to create flavor pairing knowledge for domain-adaptive pre-training.

Since FlavorDB has academic license restrictions, this approach uses the
CC0-licensed Food.com data to derive similar knowledge.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from ast import literal_eval
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from tqdm import tqdm


if TYPE_CHECKING:
    from collections.abc import Iterator

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Minimum co-occurrence count to include
MIN_COOCCURRENCE = 100

# Top N pairs to extract
TOP_PAIRS = 500

# Common "filler" ingredients to exclude from pairing analysis
FILLER_INGREDIENTS = {
    "salt",
    "pepper",
    "water",
    "oil",
    "butter",
    "flour",
    "sugar",
    "eggs",
    "egg",
    "milk",
}


def safe_literal_eval(value: str) -> list[str]:
    """Safely evaluate a string representation of a list."""
    if pd.isna(value):
        return []
    try:
        result = literal_eval(value)
        return result if isinstance(result, list) else []
    except (ValueError, SyntaxError):
        return []


def normalize_ingredient(ingredient: str) -> str:
    """Normalize ingredient name for matching."""
    return ingredient.lower().strip()


def extract_pairs(recipes_df: pd.DataFrame) -> Counter[tuple[str, str]]:
    """Extract ingredient co-occurrence pairs from recipes."""
    pairs: Counter[tuple[str, str]] = Counter()

    for _, row in tqdm(
        recipes_df.iterrows(), total=len(recipes_df), desc="Extracting pairs"
    ):
        ingredients = row["ingredients"]
        if not ingredients:
            continue

        # Normalize and filter ingredients
        normalized = [
            normalize_ingredient(ing)
            for ing in ingredients
            if normalize_ingredient(ing) not in FILLER_INGREDIENTS
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for ing in normalized:
            if ing not in seen:
                seen.add(ing)
                unique.append(ing)

        # Generate all pairs (sorted for consistency)
        for pair in combinations(sorted(unique), 2):
            pairs[pair] += 1

    return pairs


def format_pairing_knowledge(
    pairs: Counter[tuple[str, str]], min_count: int = MIN_COOCCURRENCE
) -> Iterator[dict[str, str]]:
    """Format co-occurrence pairs as training text."""
    for (ing1, ing2), count in pairs.most_common(TOP_PAIRS):
        if count < min_count:
            break

        # Generate multiple text variations for richer training
        texts = [
            f"Flavor pairing: {ing1} and {ing2} are commonly used together "
            f"(found in {count}+ recipes).",
            f"Cooking tip: {ing1.title()} pairs well with {ing2}.",
            f"Ingredient combination: {ing1.title()} and {ing2} complement each other "
            "in many recipes.",
        ]

        for text in texts:
            yield {"text": text}


def generate_category_knowledge(
    recipes_df: pd.DataFrame, pairs: Counter[tuple[str, str]]
) -> Iterator[dict[str, str]]:
    """Generate category-based pairing knowledge."""
    # Group recipes by tag categories
    category_ingredients: dict[str, Counter[str]] = {}

    for _, row in recipes_df.iterrows():
        tags = row.get("tags", [])
        ingredients = row.get("ingredients", [])

        if not tags or not ingredients:
            continue

        # Use first tag as category
        category = tags[0] if tags else "general"
        if category not in category_ingredients:
            category_ingredients[category] = Counter()

        for ing in ingredients:
            normalized = normalize_ingredient(ing)
            if normalized not in FILLER_INGREDIENTS:
                category_ingredients[category][normalized] += 1

    # Generate category-specific knowledge
    for category, ing_counts in category_ingredients.items():
        top_ingredients = [ing for ing, _ in ing_counts.most_common(10)]
        if len(top_ingredients) >= 3:
            ing_list = ", ".join(top_ingredients[:5])
            text = f"Common ingredients in {category} recipes include: {ing_list}."
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
    return file_path.stat().st_size // 4


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract ingredient co-occurrence knowledge"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Directory containing RAW_recipes.csv (Food.com data)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./data/flavor_pairs.jsonl"),
        help="Output JSONL file (default: ./data/flavor_pairs.jsonl)",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=MIN_COOCCURRENCE,
        help=f"Minimum co-occurrence count (default: {MIN_COOCCURRENCE})",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=TOP_PAIRS,
        help=f"Number of top pairs to include (default: {TOP_PAIRS})",
    )
    parser.add_argument(
        "--include-categories",
        action="store_true",
        help="Include category-based ingredient knowledge",
    )
    args = parser.parse_args()

    # Find recipes file
    recipes_path = args.input / "RAW_recipes.csv"
    if not recipes_path.exists():
        # Maybe input is the file directly
        if args.input.suffix == ".csv" and args.input.exists():
            recipes_path = args.input
        else:
            logger.error(f"Recipes file not found: {recipes_path}")
            return 1

    # Load recipes
    logger.info(f"Loading recipes from {recipes_path}...")
    recipes = pd.read_csv(recipes_path)
    logger.info(f"Loaded {len(recipes):,} recipes")

    # Parse ingredients column
    recipes["ingredients"] = recipes["ingredients"].apply(safe_literal_eval)
    if "tags" in recipes.columns:
        recipes["tags"] = recipes["tags"].apply(safe_literal_eval)

    # Extract pairs
    pairs = extract_pairs(recipes)
    logger.info(f"Found {len(pairs):,} unique ingredient pairs")
    logger.info(f"Top pairs by frequency: {pairs.most_common(10)}")

    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Generate and write knowledge
    def generate_all() -> Iterator[dict[str, str]]:
        yield from format_pairing_knowledge(pairs, args.min_count)
        if args.include_categories:
            yield from generate_category_knowledge(recipes, pairs)

    count = write_jsonl(generate_all(), args.output)
    logger.info(f"Wrote {count:,} knowledge entries to {args.output}")

    tokens = estimate_tokens(args.output)
    logger.info(f"Estimated ~{tokens:,} tokens ({tokens / 1_000_000:.1f}M)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
