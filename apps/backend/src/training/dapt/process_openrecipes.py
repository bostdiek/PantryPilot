#!/usr/bin/env python3
"""Process OpenRecipes dataset for domain-adaptive pre-training.

This script downloads and converts the OpenRecipes dataset into JSONL format
suitable for language model pre-training.

OpenRecipes is licensed under ODC-BY (Open Data Commons Attribution License)
and requires attribution for commercial use.

Source: https://github.com/fictivekin/openrecipes
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.request
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import IO, Any

from tqdm import tqdm


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# OpenRecipes data URLs (JSONL format)
OPENRECIPES_URLS = [
    "https://s3.amazonaws.com/openrecipes/20170107-061401-recipeitems.json.gz",
]

# Alternative: Raw GitHub repo with JSON files
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/fictivekin/openrecipes/master/"
    "data/recipeitems-latest.json"
)


def download_openrecipes(output_dir: Path) -> Path | None:
    """Download OpenRecipes dataset from GitHub or S3."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "openrecipes.json"

    if output_file.exists():
        logger.info(f"OpenRecipes already downloaded: {output_file}")
        return output_file

    logger.info("Downloading OpenRecipes dataset...")

    # Try GitHub raw URL first (simpler, no gzip)
    try:
        logger.info(f"Fetching from: {GITHUB_RAW_URL}")
        urllib.request.urlretrieve(GITHUB_RAW_URL, output_file)
        logger.info(f"Downloaded to {output_file}")
        return output_file
    except urllib.error.URLError as e:
        logger.warning(f"GitHub download failed: {e}")

    # If GitHub fails, try S3 (gzipped)
    import gzip

    for url in OPENRECIPES_URLS:
        try:
            logger.info(f"Trying: {url}")
            gz_file = output_dir / "openrecipes.json.gz"
            urllib.request.urlretrieve(url, gz_file)

            # Decompress
            with gzip.open(gz_file, "rb") as f_in:
                with open(output_file, "wb") as f_out:
                    f_out.write(f_in.read())

            gz_file.unlink()
            logger.info(f"Downloaded and extracted to {output_file}")
            return output_file
        except urllib.error.URLError as e:
            logger.warning(f"Download failed: {e}")
            continue

    logger.error("Failed to download OpenRecipes from all sources")
    return None


def _detect_json_format(f: IO[str]) -> str | None:
    """Detect the first non-whitespace character to determine JSON format."""
    while True:
        chunk = f.read(1024)
        if not chunk:
            break
        for ch in chunk:
            if not ch.isspace():
                return ch
    return None


def parse_openrecipes(file_path: Path) -> Iterator[dict[str, Any]]:
    """Parse OpenRecipes JSON file with streaming to avoid memory issues."""
    with open(file_path, encoding="utf-8") as f:
        first_char = _detect_json_format(f)
        f.seek(0)  # Rewind for actual parsing

        if first_char == "[":
            # JSON array format - must load into memory
            recipes = json.load(f)
            if isinstance(recipes, list):
                yield from recipes
        else:
            # JSONL format - stream line by line
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def _format_list_or_str(value: str | Sequence[Any] | None) -> str:
    """Convert list or string value to string."""
    if isinstance(value, str):
        return value
    if isinstance(value, Sequence):
        return ", ".join(str(i) for i in value if i)
    return str(value) if value else ""


def _format_instructions(instructions: str | Sequence[Any] | None) -> str:
    """Format instructions as numbered steps."""
    if isinstance(instructions, str):
        return instructions
    if isinstance(instructions, Sequence):
        return "\n".join(
            f"{i + 1}. {step}" for i, step in enumerate(instructions) if step
        )
    return str(instructions) if instructions else ""


def _format_times(recipe: Mapping[str, Any]) -> str | None:
    """Format prep/cook/total times if available."""
    prep_time = recipe.get("prepTime", "")
    cook_time = recipe.get("cookTime", "")
    total_time = recipe.get("totalTime", "")

    if not (prep_time or cook_time or total_time):
        return None

    times = []
    if prep_time:
        times.append(f"Prep: {prep_time}")
    if cook_time:
        times.append(f"Cook: {cook_time}")
    if total_time:
        times.append(f"Total: {total_time}")
    return ", ".join(times)


def format_recipe(recipe: Mapping[str, Any]) -> str | None:
    """Format an OpenRecipes entry into training text."""
    name = recipe.get("name", "").strip()
    if not name:
        return None

    ingredients = _format_list_or_str(recipe.get("ingredients", ""))
    instructions = _format_instructions(recipe.get("recipeInstructions", ""))

    # Skip recipes without meaningful content
    if not ingredients and not instructions:
        return None

    # Build text
    text = f"# {name}\n\n"

    # Add source attribution (required by ODC-BY)
    source = recipe.get("source", recipe.get("url", "OpenRecipes"))
    if source:
        text += f"Source: {source}\n\n"

    # Add times if available
    times = _format_times(recipe)
    if times:
        text += f"Time: {times}\n\n"

    if ingredients:
        text += f"## Ingredients\n{ingredients}\n\n"

    if instructions:
        text += f"## Instructions\n{instructions}\n"

    # Add description if available
    description = recipe.get("description", "")
    if description and isinstance(description, str) and len(description) > 20:
        text += f"\n## About\n{description.strip()}\n"

    return text


def process_openrecipes(input_path: Path) -> Iterator[dict[str, str]]:
    """Process OpenRecipes and yield JSONL records."""
    logger.info(f"Processing OpenRecipes from {input_path}...")

    count = 0
    skipped = 0

    for recipe in tqdm(parse_openrecipes(input_path), desc="Processing recipes"):
        text = format_recipe(recipe)
        if text:
            yield {"text": text}
            count += 1
        else:
            skipped += 1

    logger.info(f"Processed {count:,} recipes, skipped {skipped:,}")


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
    return file_size // 4


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process OpenRecipes dataset for pre-training"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./data/openrecipes_corpus.jsonl"),
        help="Output JSONL file (default: ./data/openrecipes_corpus.jsonl)",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path("./data/openrecipes"),
        help="Directory for downloaded data (default: ./data/openrecipes)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Use existing OpenRecipes JSON file instead of downloading",
    )
    args = parser.parse_args()

    # Download or use existing file
    if args.input:
        input_path = args.input
        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            return 1
    else:
        input_path = download_openrecipes(args.download_dir)
        if input_path is None:
            return 1

    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Process and write
    count = write_jsonl(process_openrecipes(input_path), args.output)
    logger.info(f"Wrote {count:,} recipes to {args.output}")

    tokens = estimate_tokens(args.output)
    logger.info(f"Estimated ~{tokens:,} tokens ({tokens / 1_000_000:.1f}M)")

    # Attribution notice
    logger.info("\n" + "=" * 60)
    logger.info("ATTRIBUTION NOTICE (ODC-BY License)")
    logger.info("=" * 60)
    logger.info(
        "This corpus includes data from OpenRecipes "
        "(https://github.com/fictivekin/openrecipes)"
    )
    logger.info("Licensed under Open Data Commons Attribution License (ODC-BY)")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
