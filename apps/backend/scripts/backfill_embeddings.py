#!/usr/bin/env python3
"""Backfill embeddings for existing recipes with progress tracking."""

import asyncio
import logging
import sys
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from dependencies.db import AsyncSessionLocal
from models.recipes_names import Recipe
from services.embedding_service import generate_recipe_embedding


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 10
DELAY_BETWEEN_BATCHES = 1.0  # seconds
DELAY_ON_RATE_LIMIT = 30.0  # seconds
MAX_RETRIES = 3


async def get_pending_count(session) -> int:
    """Get count of recipes needing embeddings."""
    result = await session.execute(
        select(func.count(Recipe.id)).where(Recipe.embedding.is_(None))
    )
    return result.scalar() or 0


async def backfill_embeddings(
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    """Backfill embeddings for all recipes without one.

    Args:
        dry_run: If True, don't actually update the database
        limit: Maximum number of recipes to process (None for all)

    Returns:
        Summary statistics
    """
    stats = {
        "total_pending": 0,
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "start_time": datetime.now(UTC),
    }

    async with AsyncSessionLocal() as session:
        stats["total_pending"] = await get_pending_count(session)
        logger.info(f"📊 Found {stats['total_pending']} recipes needing embeddings")

        if dry_run:
            logger.info("🔍 DRY RUN - no changes will be made")
            return stats

        processed = 0
        while True:
            # Check limit
            if limit and processed >= limit:
                logger.info(f"🛑 Reached limit of {limit} recipes")
                break

            # Get batch of recipes without embeddings
            stmt = (
                select(Recipe)
                .where(Recipe.embedding.is_(None))
                .options(
                    selectinload(Recipe.recipeingredients).selectinload(
                        lambda ri: ri.ingredient
                    )
                )
                .limit(min(BATCH_SIZE, (limit - processed) if limit else BATCH_SIZE))
            )

            result = await session.execute(stmt)
            recipes = result.scalars().all()

            if not recipes:
                logger.info("✅ All recipes have embeddings!")
                break

            # Process batch
            for recipe in recipes:
                processed += 1
                stats["processed"] = processed

                for attempt in range(MAX_RETRIES):
                    try:
                        embedding = await generate_recipe_embedding(recipe)
                        recipe.embedding = embedding
                        stats["succeeded"] += 1
                        remaining = stats["total_pending"] - processed
                        logger.info(
                            f"✓ [{processed}/{stats['total_pending']}] "
                            f"{recipe.name[:40]}... ({remaining} remaining)"
                        )
                        break

                    except Exception as e:
                        if "rate" in str(e).lower() and attempt < MAX_RETRIES - 1:
                            logger.warning(
                                f"⏳ Rate limited, waiting {DELAY_ON_RATE_LIMIT}s..."
                            )
                            await asyncio.sleep(DELAY_ON_RATE_LIMIT)
                        else:
                            stats["failed"] += 1
                            logger.error(f"✗ Failed: {recipe.name} - {e}")
                            break

            await session.commit()
            logger.info(f"💾 Committed batch of {len(recipes)} recipes")

            # Rate limiting between batches
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    stats["end_time"] = datetime.now(UTC)
    stats["duration_seconds"] = (
        stats["end_time"] - stats["start_time"]
    ).total_seconds()

    return stats


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Backfill embeddings for recipes")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making changes",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Maximum number of recipes to process"
    )
    args = parser.parse_args()

    stats = asyncio.run(
        backfill_embeddings(
            dry_run=args.dry_run,
            limit=args.limit,
        )
    )

    print("\n" + "=" * 50)
    print("📈 BACKFILL SUMMARY")
    print("=" * 50)
    print(f"Total pending: {stats['total_pending']}")
    print(f"Processed:     {stats['processed']}")
    print(f"Succeeded:     {stats['succeeded']}")
    print(f"Failed:        {stats['failed']}")
    if "duration_seconds" in stats:
        print(f"Duration:      {stats['duration_seconds']:.1f}s")
    print("=" * 50)

    sys.exit(0 if stats["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
