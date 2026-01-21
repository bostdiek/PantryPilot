"""Tool for searching user's saved recipes with hybrid search."""

from __future__ import annotations

from typing import Any, Literal

from pydantic_ai import RunContext
from sqlalchemy import and_, desc, func, or_, select, text

from models.meal_history import Meal
from models.recipes_names import Recipe
from services.chat_agent.deps import ChatAgentDeps
from services.embedding_service import generate_query_embedding


SortBy = Literal["relevance", "name", "times_cooked", "cook_time"]


async def tool_search_recipes(
    ctx: RunContext[ChatAgentDeps],
    query: str | None = None,
    cuisine: str | None = None,
    difficulty: Literal["easy", "medium", "hard"] | None = None,
    max_cook_time: int | None = None,
    min_times_cooked: int | None = None,
    sort_by: SortBy = "relevance",
) -> dict[str, Any]:
    """Search user's saved recipes using semantic search and/or metadata filters.

    This tool searches through the user's persisted recipe collection.
    Use it to find recipes they've already saved, not for new suggestions.

    Examples:
    - "Find my chicken recipes" → query="chicken"
    - "What comfort food do I have?" → query="comfort food"
    - "Quick Italian recipes" → query="italian", max_cook_time=30
    - "Easy recipes I've cooked often" → difficulty="easy", min_times_cooked=3
    - "Show all my Mexican recipes" → cuisine="mexican"

    Args:
        query: Natural language search (semantic + fuzzy text matching)
        cuisine: Filter by cuisine type (italian, mexican, asian, etc.)
        difficulty: Filter by difficulty level
        max_cook_time: Maximum total cooking time in minutes
        min_times_cooked: Minimum number of times you've cooked this recipe
        sort_by: How to order results

    Returns:
        Matching recipes ranked by relevance/filters with metadata
    """
    max_results = 15  # Hardcoded limit

    # Build times_cooked subquery
    times_cooked_sq = (
        select(Meal.recipe_id, func.count(Meal.id).label("cook_count"))
        .where(
            and_(
                Meal.user_id == ctx.deps.user.id,
                Meal.was_cooked == True,  # noqa: E712
            )
        )
        .group_by(Meal.recipe_id)
        .subquery()
    )

    # Case 1: Query provided - use hybrid search with optional filters
    if query:
        query_embedding = await generate_query_embedding(query)

        # Build filter conditions for WHERE clause
        filter_conditions = []
        if cuisine:
            filter_conditions.append(f"AND ethnicity ILIKE '%{cuisine}%'")
        if difficulty:
            filter_conditions.append(f"AND difficulty ILIKE '{difficulty}'")
        if max_cook_time:
            filter_conditions.append(f"AND total_time_minutes <= {max_cook_time}")

        filter_sql = " ".join(filter_conditions)

        # Hybrid search with RRF
        hybrid_sql = text(
            f"""
            WITH text_search AS (
                SELECT id, name, description, ethnicity, difficulty,
                       total_time_minutes, link_source,
                       ROW_NUMBER() OVER (
                           ORDER BY similarity(name, :query) DESC
                       ) as text_rank
                FROM recipe_names
                WHERE (user_id = :user_id OR user_id IS NULL)
                  AND (name % :query OR description % :query)
                  {filter_sql}
                LIMIT 20
            ),
            vector_search AS (
                SELECT id, name, description, ethnicity, difficulty,
                       total_time_minutes, link_source,
                       ROW_NUMBER() OVER (
                           ORDER BY embedding <=> :embedding
                       ) as vector_rank
                FROM recipe_names
                WHERE (user_id = :user_id OR user_id IS NULL)
                  AND embedding IS NOT NULL
                  {filter_sql}
                LIMIT 20
            ),
            times_cooked_cte AS (
                SELECT recipe_id, COUNT(id) as cook_count
                FROM meal_history
                WHERE user_id = :user_id AND was_cooked = true
                GROUP BY recipe_id
            )
            SELECT
                COALESCE(t.id, v.id) as id,
                COALESCE(t.name, v.name) as name,
                COALESCE(t.description, v.description) as description,
                COALESCE(t.ethnicity, v.ethnicity) as ethnicity,
                COALESCE(t.difficulty, v.difficulty) as difficulty,
                COALESCE(t.total_time_minutes, v.total_time_minutes)
                    as total_time_minutes,
                COALESCE(t.link_source, v.link_source) as link_source,
                COALESCE(tc.cook_count, 0) as times_cooked,
                (COALESCE(1.0 / (60 + t.text_rank), 0) +
                 COALESCE(1.0 / (60 + v.vector_rank), 0)) as rrf_score
            FROM text_search t
            FULL OUTER JOIN vector_search v ON t.id = v.id
            LEFT JOIN times_cooked_cte tc ON COALESCE(t.id, v.id) = tc.recipe_id
            WHERE (:min_times_cooked IS NULL
                   OR COALESCE(tc.cook_count, 0) >= :min_times_cooked)
            ORDER BY rrf_score DESC
            LIMIT :limit
        """
        )

        result = await ctx.deps.db.execute(
            hybrid_sql,
            {
                "query": query,
                "user_id": ctx.deps.user.id,
                "embedding": query_embedding,
                "min_times_cooked": min_times_cooked,
                "limit": max_results,
            },
        )

        recipes = result.mappings().all()

        return {
            "status": "ok",
            "query": query,
            "filters_applied": {
                "cuisine": cuisine,
                "difficulty": difficulty,
                "max_cook_time": max_cook_time,
                "min_times_cooked": min_times_cooked,
            },
            "total_results": len(recipes),
            "recipes": [
                {
                    "id": str(r["id"]),
                    "name": r["name"],
                    "description": r["description"],
                    "cuisine": r["ethnicity"],
                    "difficulty": r["difficulty"],
                    "total_time_minutes": r["total_time_minutes"],
                    "source_url": r["link_source"],
                    "times_cooked": r["times_cooked"],
                    "relevance_score": round(r["rrf_score"], 4),
                }
                for r in recipes
            ],
        }

    # Case 2: No query - use metadata filters only
    else:
        stmt = (
            select(
                Recipe,
                func.coalesce(times_cooked_sq.c.cook_count, 0).label("times_cooked"),
            )
            .outerjoin(times_cooked_sq, Recipe.id == times_cooked_sq.c.recipe_id)
            .where(
                or_(
                    Recipe.user_id == ctx.deps.user.id,
                    Recipe.user_id.is_(None),
                )
            )
        )

        # Apply filters
        filters: list[Any] = []

        if cuisine:
            filters.append(Recipe.ethnicity.ilike(f"%{cuisine}%"))

        if difficulty:
            filters.append(Recipe.difficulty.ilike(difficulty))

        if max_cook_time:
            filters.append(Recipe.total_time_minutes <= max_cook_time)

        if min_times_cooked:
            filters.append(
                func.coalesce(times_cooked_sq.c.cook_count, 0) >= min_times_cooked
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        # Apply sorting
        sort_map = {
            "name": Recipe.name.asc(),
            "times_cooked": desc(func.coalesce(times_cooked_sq.c.cook_count, 0)),
            "cook_time": Recipe.total_time_minutes.asc(),
            "relevance": Recipe.name.asc(),  # Fallback to name when no query
        }
        stmt = stmt.order_by(sort_map.get(sort_by, Recipe.name.asc()))
        stmt = stmt.limit(max_results)

        result = await ctx.deps.db.execute(stmt)
        rows = result.all()

        return {
            "status": "ok",
            "query": None,
            "filters_applied": {
                "cuisine": cuisine,
                "difficulty": difficulty,
                "max_cook_time": max_cook_time,
                "min_times_cooked": min_times_cooked,
            },
            "sort_by": sort_by,
            "total_results": len(rows),
            "recipes": [
                {
                    "id": str(recipe.id),
                    "name": recipe.name,
                    "description": recipe.description,
                    "cuisine": recipe.ethnicity,
                    "difficulty": recipe.difficulty,
                    "total_time_minutes": recipe.total_time_minutes,
                    "source_url": recipe.link_source,
                    "times_cooked": times_cooked,
                }
                for recipe, times_cooked in rows
            ],
        }
