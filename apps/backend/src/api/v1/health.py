import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from dependencies.db import get_db
from models.recipes_names import Recipe
from schemas.api import ApiResponse


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=ApiResponse[dict[str, str]])
def health_check() -> ApiResponse[dict[str, str]]:
    """Health check endpoint for monitoring and load balancer health checks."""
    return ApiResponse(
        success=True,
        data={"status": "healthy", "message": "SmartMealPlanner API is running"},
        message="Health check successful",
    )


@router.get("/health/embeddings", response_model=ApiResponse[dict[str, object]])
async def embedding_health_check(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, object]]:
    """Check embedding model consistency across recipes.

    Returns statistics about embeddings including counts of:
    - Total recipes with embeddings
    - Recipes using current embedding model
    - Recipes using outdated embedding models
    """
    settings = get_settings()
    current_model = settings.EMBEDDING_MODEL

    # Count total embeddings
    total_result = await db.execute(
        select(func.count(Recipe.id)).where(Recipe.embedding.isnot(None))
    )
    total_with_embeddings = total_result.scalar() or 0

    # Count embeddings with current model
    current_result = await db.execute(
        select(func.count(Recipe.id)).where(
            Recipe.embedding.isnot(None),
            Recipe.embedding_model == current_model,
        )
    )
    current_model_count = current_result.scalar() or 0

    # Count embeddings without model tracking (legacy)
    legacy_result = await db.execute(
        select(func.count(Recipe.id)).where(
            Recipe.embedding.isnot(None),
            Recipe.embedding_model.is_(None),
        )
    )
    legacy_count = legacy_result.scalar() or 0

    # Count outdated embeddings (different model, not null)
    outdated_count = total_with_embeddings - current_model_count - legacy_count

    # Log warning if there are outdated embeddings
    if outdated_count > 0 or legacy_count > 0:
        logger.warning(
            f"Embedding model mismatch detected: {outdated_count} outdated, "
            f"{legacy_count} legacy (no model recorded). "
            f"Current model: {current_model}. "
            f"Run backfill_embeddings.py --outdated-model to update."
        )

    return ApiResponse(
        success=True,
        data={
            "current_model": current_model,
            "total_with_embeddings": total_with_embeddings,
            "current_model_count": current_model_count,
            "legacy_count": legacy_count,
            "outdated_count": outdated_count,
            "needs_update": outdated_count > 0 or legacy_count > 0,
        },
        message="Embedding health check complete",
    )
