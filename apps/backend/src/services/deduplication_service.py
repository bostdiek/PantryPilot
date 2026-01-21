"""Deduplication service for recipes and ingredients."""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession


if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Similarity threshold for fuzzy matching (0.0-1.0)
RECIPE_SIMILARITY_THRESHOLD = 0.8
INGREDIENT_SIMILARITY_THRESHOLD = 0.85


def generate_ingredient_hash(ingredient_names: list[str]) -> str:
    """Generate a hash of sorted, normalized ingredient names.

    Used for quick duplicate detection based on ingredients.
    """
    normalized = sorted(name.lower().strip() for name in ingredient_names)
    return hashlib.sha256("|".join(normalized).encode()).hexdigest()[:16]


async def check_recipe_duplicate(
    db: AsyncSession,
    user_id: UUID,
    name: str,
    ingredient_names: list[str] | None = None,
) -> dict[str, Any]:
    """Check if a recipe is a potential duplicate.

    Returns:
        {
            "is_duplicate": bool,
            "exact_match": Recipe | None,
            "similar_matches": list[dict],
            "reason": str | None,
        }
    """
    from models.recipes_names import Recipe

    result: dict[str, Any] = {
        "is_duplicate": False,
        "exact_match": None,
        "similar_matches": [],
        "reason": None,
    }

    # 1. Check for exact name match (same user)
    exact_stmt = select(Recipe).where(
        and_(
            Recipe.user_id == user_id,
            func.lower(Recipe.name) == name.lower().strip(),
        )
    )
    exact_result = await db.execute(exact_stmt)
    exact = exact_result.scalars().first()

    if exact:
        result["is_duplicate"] = True
        result["exact_match"] = exact
        result["reason"] = f"Exact name match: '{exact.name}'"
        return result

    # 2. Check for fuzzy name match using trigram similarity
    fuzzy_stmt = text(
        """
        SELECT id, name, similarity(name, :name) as sim
        FROM recipe_names
        WHERE user_id = :user_id
          AND similarity(name, :name) > :threshold
        ORDER BY sim DESC
        LIMIT 5
    """
    )

    fuzzy_result = await db.execute(
        fuzzy_stmt,
        {
            "name": name,
            "user_id": user_id,
            "threshold": RECIPE_SIMILARITY_THRESHOLD,
        },
    )
    similar = fuzzy_result.mappings().all()

    if similar:
        result["similar_matches"] = [
            {"id": str(r["id"]), "name": r["name"], "similarity": round(r["sim"], 2)}
            for r in similar
        ]
        if similar[0]["sim"] > 0.95:
            result["is_duplicate"] = True
            result["reason"] = (
                f"Very similar name: '{similar[0]['name']}' "
                f"({similar[0]['sim']:.0%} match)"
            )

    return result


async def check_ingredient_duplicate(
    db: AsyncSession,
    user_id: UUID | None,
    ingredient_name: str,
) -> dict[str, Any]:
    """Check if an ingredient is a potential duplicate.

    Returns:
        {
            "is_duplicate": bool,
            "exact_match": Ingredient | None,
            "similar_matches": list[dict],
        }
    """
    from models.ingredient_names import Ingredient

    result: dict[str, Any] = {
        "is_duplicate": False,
        "exact_match": None,
        "similar_matches": [],
    }

    # Check exact match
    exact_stmt = select(Ingredient).where(
        and_(
            Ingredient.user_id == user_id,
            func.lower(Ingredient.ingredient_name) == ingredient_name.lower().strip(),
        )
    )
    exact_result = await db.execute(exact_stmt)
    exact = exact_result.scalars().first()

    if exact:
        result["is_duplicate"] = True
        result["exact_match"] = exact
        return result

    # Check fuzzy match
    fuzzy_stmt = text(
        """
        SELECT id, ingredient_name, similarity(ingredient_name, :name) as sim
        FROM ingredient_names
        WHERE user_id = :user_id
          AND similarity(ingredient_name, :name) > :threshold
        ORDER BY sim DESC
        LIMIT 3
    """
    )

    fuzzy_result = await db.execute(
        fuzzy_stmt,
        {
            "name": ingredient_name,
            "user_id": user_id,
            "threshold": INGREDIENT_SIMILARITY_THRESHOLD,
        },
    )
    similar = fuzzy_result.mappings().all()

    if similar:
        result["similar_matches"] = [
            {
                "id": str(r["id"]),
                "name": r["ingredient_name"],
                "similarity": round(r["sim"], 2),
            }
            for r in similar
        ]
        if similar[0]["sim"] > 0.95:
            result["is_duplicate"] = True
            result["exact_match_id"] = similar[0]["id"]

    return result


async def find_duplicate_recipes(
    db: AsyncSession,
    user_id: UUID | None = None,
    similarity_threshold: float = 0.85,
) -> list[dict[str, Any]]:
    """Find all potential duplicate recipes in the database.

    For cleanup/reporting purposes.
    """
    # Self-join to find similar recipe pairs
    stmt = text(
        """
        SELECT
            r1.id as id1, r1.name as name1, r1.user_id as user_id1,
            r2.id as id2, r2.name as name2, r2.user_id as user_id2,
            similarity(r1.name, r2.name) as sim
        FROM recipe_names r1
        JOIN recipe_names r2
            ON r1.id < r2.id  -- Avoid duplicates and self-matches
            AND similarity(r1.name, r2.name) > :threshold
        WHERE (:user_id IS NULL OR r1.user_id = :user_id)
        ORDER BY sim DESC
        LIMIT 100
    """
    )

    result = await db.execute(
        stmt, {"threshold": similarity_threshold, "user_id": user_id}
    )
    duplicates = result.mappings().all()

    return [
        {
            "recipe_1": {"id": str(d["id1"]), "name": d["name1"]},
            "recipe_2": {"id": str(d["id2"]), "name": d["name2"]},
            "similarity": round(d["sim"], 2),
        }
        for d in duplicates
    ]
