#!/usr/bin/env python3
"""Backfill embeddings for existing recipes with progress tracking.

Supports:
- Backfilling recipes without embeddings
- Re-embedding all recipes (--force-all)
- Re-embedding recipes with outdated models (--outdated-model)
- Automatic REINDEX after bulk updates
"""

import asyncio
import logging
import sys
from datetime import UTC, datetime

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import selectinload

from dependencies.db import AsyncSessionLocal
from models.recipe_ingredients import RecipeIngredient
from models.recipes_names import Recipe
from services.ai.model_factory import get_current_embedding_model_name
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


async def get_pending_count(
    session,
    force_all: bool = False,
    outdated_model: str | None = None,
) -> int:
    """Get count of recipes needing embeddings."""
    if force_all:
        # Count all recipes
        result = await session.execute(select(func.count(Recipe.id)))
    elif outdated_model:
        # Count recipes with specific outdated model or no model recorded
        result = await session.execute(
            select(func.count(Recipe.id)).where(
                or_(
                    Recipe.embedding_model == outdated_model,
                    Recipe.embedding_model.is_(None),
                )
            )
        )
    else:
        # Count recipes without embeddings
        result = await session.execute(
            select(func.count(Recipe.id)).where(Recipe.embedding.is_(None))
        )
    return result.scalar() or 0


async def get_outdated_model_stats(session) -> dict[str, int]:
    """Get counts of recipes by embedding model."""
    current_model = get_current_embedding_model_name()
    stats = {"current_model": current_model}

    # Group by embedding_model
    result = await session.execute(
        select(Recipe.embedding_model, func.count(Recipe.id))
        .where(Recipe.embedding.isnot(None))
        .group_by(Recipe.embedding_model)
    )
    for model, count in result.all():
        model_key = model if model else "(no model recorded)"
        stats[model_key] = count

    return stats


async def reindex_embedding_index(session) -> None:
    """Reindex the embedding vector index for optimal search performance."""
    logger.info("🔄 Reindexing embedding vector index...")
    try:
        await session.execute(
            text("REINDEX INDEX CONCURRENTLY idx_recipe_names_embedding")
        )
        logger.info("✅ Embedding index reindexed successfully")
    except Exception as e:
        logger.warning(f"⚠️ Failed to reindex (may not exist yet): {e}")


def _build_where_clause(force_all: bool, outdated_model: str | None):
    """Build the WHERE clause based on processing mode."""
    if force_all:
        return True  # All recipes
    if outdated_model:
        return or_(
            Recipe.embedding_model == outdated_model,
            Recipe.embedding_model.is_(None),
        )
    return Recipe.embedding.is_(None)


async def _process_single_recipe(recipe, stats: dict, processed: int) -> bool:
    """Process a single recipe with retry logic.

    Returns True if successful, False if failed.
    """
    for attempt in range(MAX_RETRIES):
        try:
            context, embedding, model_name = await generate_recipe_embedding(recipe)
            recipe.search_context = context
            recipe.embedding = embedding
            recipe.embedding_model = model_name
            recipe.search_context_generated_at = datetime.now(UTC)
            recipe.embedding_generated_at = datetime.now(UTC)
            stats["succeeded"] += 1
            remaining = stats["total_pending"] - processed
            logger.info(
                f"✓ [{processed}/{stats['total_pending']}] "
                f"{recipe.name[:40]}... ({remaining} remaining)"
            )
            return True
        except Exception as e:
            if "rate" in str(e).lower() and attempt < MAX_RETRIES - 1:
                logger.warning(f"⏳ Rate limited, waiting {DELAY_ON_RATE_LIMIT}s...")
                await asyncio.sleep(DELAY_ON_RATE_LIMIT)
            else:
                stats["failed"] += 1
                logger.error(f"✗ Failed: {recipe.name} - {e}")
                return False
    return False


async def backfill_embeddings(
    dry_run: bool = False,
    limit: int | None = None,
    force_all: bool = False,
    outdated_model: str | None = None,
) -> dict:
    """Backfill embeddings for recipes.

    Args:
        dry_run: If True, don't actually update the database
        limit: Maximum number of recipes to process (None for all)
        force_all: If True, regenerate embeddings for ALL recipes
        outdated_model: If set, only update recipes with this model name

    Returns:
        Summary statistics
    """
    stats = {
        "total_pending": 0,
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "start_time": datetime.now(UTC),
        "mode": (
            "force_all" if force_all else ("outdated" if outdated_model else "missing")
        ),
    }

    async with AsyncSessionLocal() as session:
        # Show model statistics
        model_stats = await get_outdated_model_stats(session)
        logger.info(f"📊 Embedding model statistics: {model_stats}")

        stats["total_pending"] = await get_pending_count(
            session, force_all=force_all, outdated_model=outdated_model
        )
        logger.info(f"📊 Found {stats['total_pending']} recipes to process")

        if dry_run:
            logger.info("🔍 DRY RUN - no changes will be made")
            return stats

        where_clause = _build_where_clause(force_all, outdated_model)
        processed = 0

        while True:
            # Check limit
            if limit and processed >= limit:
                logger.info(f"🛑 Reached limit of {limit} recipes")
                break

            # Get batch of recipes
            stmt = (
                select(Recipe)
                .where(where_clause)
                .options(
                    selectinload(Recipe.recipeingredients).selectinload(
                        RecipeIngredient.ingredient
                    )
                )
                .limit(min(BATCH_SIZE, (limit - processed) if limit else BATCH_SIZE))
            )

            result = await session.execute(stmt)
            recipes = result.scalars().all()

            if not recipes:
                logger.info("✅ All targeted recipes have been processed!")
                break

            # Process batch
            for recipe in recipes:
                processed += 1
                stats["processed"] = processed
                await _process_single_recipe(recipe, stats, processed)

            await session.commit()
            logger.info(f"💾 Committed batch of {len(recipes)} recipes")

            # Rate limiting between batches
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

        # Reindex embedding index after bulk updates
        if stats["succeeded"] > 0:
            await reindex_embedding_index(session)

    stats["end_time"] = datetime.now(UTC)
    stats["duration_seconds"] = (
        stats["end_time"] - stats["start_time"]
    ).total_seconds()

    return stats


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Backfill embeddings for recipes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backfill only recipes without embeddings
  python backfill_embeddings.py

  # Preview what would be processed
  python backfill_embeddings.py --dry-run

  # Force regenerate ALL embeddings (after model change)
  python backfill_embeddings.py --force-all

  # Update only recipes using a specific outdated model
  python backfill_embeddings.py --outdated-model gemini-embedding-exp-001

  # Limit processing for testing
  python backfill_embeddings.py --limit 10
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making changes",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Maximum number of recipes to process"
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Regenerate embeddings for ALL recipes (use after model changes)",
    )
    parser.add_argument(
        "--outdated-model",
        type=str,
        default=None,
        help="Only update recipes with this specific embedding model name",
    )
    args = parser.parse_args()

    # Validate mutually exclusive options
    if args.force_all and args.outdated_model:
        parser.error("--force-all and --outdated-model are mutually exclusive")

    current_model = get_current_embedding_model_name()
    print(f"🔧 Current embedding model: {current_model}")

    stats = asyncio.run(
        backfill_embeddings(
            dry_run=args.dry_run,
            limit=args.limit,
            force_all=args.force_all,
            outdated_model=args.outdated_model,
        )
    )

    print("\n" + "=" * 50)
    print("📈 BACKFILL SUMMARY")
    print("=" * 50)
    print(f"Mode:          {stats.get('mode', 'missing')}")
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
