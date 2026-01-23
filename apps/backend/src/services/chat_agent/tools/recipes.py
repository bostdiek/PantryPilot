"""Tool for searching user's saved recipes with hybrid search.

Implementation note:
- Uses two simple queries (text + vector) and merges results in Python.
- Avoids raw SQL with optional NULL parameters, which can be brittle with asyncpg.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic_ai import RunContext
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import selectinload

from models.meal_history import Meal
from models.recipe_ingredients import RecipeIngredient
from models.recipes_names import Recipe
from schemas.recipes import RecipeCategory, RecipeDifficulty, RecipeOut
from services.chat_agent.deps import ChatAgentDeps
from services.embedding_service import generate_query_embedding


SortBy = Literal["relevance", "name", "times_cooked", "cook_time"]


# pg_trgm's `%` operator uses a session-level similarity threshold (often 0.3).
# For short queries like "phad thai", that threshold can be too strict, causing
# expected near-matches to be filtered out. We apply our own lower bound.
MIN_TEXT_SIMILARITY = 0.10


def _rrf_score(*, text_rank: int | None, vector_rank: int | None, k: int) -> float:
    score = 0.0
    if text_rank is not None:
        score += 1.0 / (k + text_rank)
    if vector_rank is not None:
        score += 1.0 / (k + vector_rank)
    return score


def _recipe_to_full_payload(recipe: Recipe) -> dict[str, Any]:
    now_ts = datetime.now(UTC)
    response_data: dict[str, Any] = {
        "id": recipe.id,
        "title": recipe.name,
        "description": recipe.description,
        "prep_time_minutes": int(recipe.prep_time_minutes or 0),
        "cook_time_minutes": int(recipe.cook_time_minutes or 0),
        "total_time_minutes": int(recipe.total_time_minutes or 0),
        "serving_min": int(recipe.serving_min or 1),
        "serving_max": recipe.serving_max,
        "instructions": recipe.instructions or [],
        "difficulty": RecipeDifficulty(
            recipe.difficulty or RecipeDifficulty.MEDIUM.value
        ),
        "category": (
            RecipeCategory(recipe.course_type)
            if recipe.course_type
            else RecipeCategory.LUNCH
        ),
        "ethnicity": recipe.ethnicity,
        "oven_temperature_f": recipe.oven_temperature_f,
        "user_notes": recipe.user_notes,
        "link_source": recipe.link_source,
        "created_at": recipe.created_at or now_ts,
        "updated_at": recipe.updated_at or now_ts,
        "ai_summary": recipe.ai_summary,
        "ingredients": [],
    }

    for ri in list(recipe.recipeingredients or []):
        prep_raw: Any = ri.prep or {}
        if isinstance(prep_raw, dict):
            method = prep_raw.get("method")
            size_descriptor = prep_raw.get("size_descriptor") or prep_raw.get(
                "size_unit"
            )
            prep_out = (
                None
                if (method is None and size_descriptor is None)
                else {
                    "method": method,
                    "size_descriptor": size_descriptor,
                }
            )
        else:
            prep_out = None

        response_data["ingredients"].append(
            {
                "id": ri.id,
                "name": ri.ingredient.ingredient_name,
                "quantity_value": ri.quantity_value,
                "quantity_unit": ri.quantity_unit,
                "prep": prep_out,
                "is_optional": ri.is_optional,
            }
        )

    recipe_out = RecipeOut(**response_data)
    return recipe_out.model_dump(mode="json")


async def _load_full_recipes(
    *,
    ctx: RunContext[ChatAgentDeps],
    recipes: list[Recipe],
) -> dict[str, dict[str, Any]]:
    if not recipes:
        return {}

    recipe_ids = list({r.id for r in recipes})

    # Ensure any pending operations are complete before new query
    await ctx.deps.db.flush()

    stmt = (
        select(Recipe)
        .where(Recipe.id.in_(recipe_ids))
        .options(
            selectinload(Recipe.recipeingredients).selectinload(
                RecipeIngredient.ingredient
            )
        )
    )
    result = await ctx.deps.db.execute(stmt)
    full_recipes = result.scalars().all()
    return {str(r.id): _recipe_to_full_payload(r) for r in full_recipes}


def _apply_optional_filters(
    *,
    predicates: list[Any],
    cuisine: str | None,
    difficulty: str | None,
    max_cook_time: int | None,
    min_times_cooked: int | None,
    times_cooked_expr: Any,
) -> None:
    if cuisine:
        predicates.append(Recipe.ethnicity.ilike(f"%{cuisine}%"))
    if difficulty:
        predicates.append(Recipe.difficulty.ilike(difficulty))
    if max_cook_time is not None:
        predicates.append(Recipe.total_time_minutes <= max_cook_time)
    if min_times_cooked is not None:
        predicates.append(times_cooked_expr >= min_times_cooked)


async def _hybrid_search_with_query(
    *,
    ctx: RunContext[ChatAgentDeps],
    query: str,
    query_embedding: list[float],
    times_cooked_sq: Any,
    cuisine: str | None,
    difficulty: str | None,
    max_cook_time: int | None,
    min_times_cooked: int | None,
    sort_by: SortBy,
    max_results: int,
    cte_limit: int,
    rrf_k: int,
) -> list[dict[str, Any]]:
    base_predicates: list[Any] = [
        or_(
            Recipe.user_id == ctx.deps.user.id,
            Recipe.user_id.is_(None),
        )
    ]

    times_cooked_expr = func.coalesce(times_cooked_sq.c.cook_count, 0)
    _apply_optional_filters(
        predicates=base_predicates,
        cuisine=cuisine,
        difficulty=difficulty,
        max_cook_time=max_cook_time,
        min_times_cooked=min_times_cooked,
        times_cooked_expr=times_cooked_expr,
    )

    name_similarity = func.coalesce(func.similarity(Recipe.name, query), 0.0)
    desc_similarity = func.coalesce(func.similarity(Recipe.description, query), 0.0)
    best_similarity = func.greatest(name_similarity, desc_similarity)
    query_like = f"%{query}%"
    text_stmt = (
        select(Recipe, times_cooked_expr.label("times_cooked"))
        .outerjoin(times_cooked_sq, Recipe.id == times_cooked_sq.c.recipe_id)
        .where(and_(*base_predicates))
        .where(
            or_(
                Recipe.name.ilike(query_like),
                Recipe.description.ilike(query_like),
                name_similarity >= MIN_TEXT_SIMILARITY,
                desc_similarity >= MIN_TEXT_SIMILARITY,
            )
        )
        .order_by(best_similarity.desc())
        .limit(cte_limit)
    )

    # Use pgvector's native cosine_distance - fully parameterized, safe
    vector_distance = Recipe.embedding.cosine_distance(query_embedding)
    vector_stmt = (
        select(Recipe, times_cooked_expr.label("times_cooked"))
        .outerjoin(times_cooked_sq, Recipe.id == times_cooked_sq.c.recipe_id)
        .where(and_(*base_predicates))
        .where(Recipe.embedding.is_not(None))
        .order_by(vector_distance.asc())
        .limit(cte_limit)
    )

    text_rows = (await ctx.deps.db.execute(text_stmt)).all()
    vector_rows = (await ctx.deps.db.execute(vector_stmt)).all()

    combined: dict[str, dict[str, Any]] = {}

    for rank, (recipe, times_cooked) in enumerate(text_rows, start=1):
        key = str(recipe.id)
        combined.setdefault(
            key,
            {
                "recipe": recipe,
                "times_cooked": int(times_cooked or 0),
                "text_rank": None,
                "vector_rank": None,
            },
        )
        combined[key]["text_rank"] = rank

    for rank, (recipe, times_cooked) in enumerate(vector_rows, start=1):
        key = str(recipe.id)
        combined.setdefault(
            key,
            {
                "recipe": recipe,
                "times_cooked": int(times_cooked or 0),
                "text_rank": None,
                "vector_rank": None,
            },
        )
        combined[key]["vector_rank"] = rank

    items = list(combined.values())
    if sort_by == "name":
        items.sort(key=lambda x: (x["recipe"].name or "").lower())
    elif sort_by == "times_cooked":
        items.sort(key=lambda x: x["times_cooked"], reverse=True)
    elif sort_by == "cook_time":
        items.sort(
            key=lambda x: x["recipe"].total_time_minutes
            if x["recipe"].total_time_minutes is not None
            else 10**9
        )
    else:
        items.sort(
            key=lambda x: _rrf_score(
                text_rank=x["text_rank"],
                vector_rank=x["vector_rank"],
                k=rrf_k,
            ),
            reverse=True,
        )

    return items[:max_results]


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
    cte_limit = 20
    rrf_k = 60

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
        items = await _hybrid_search_with_query(
            ctx=ctx,
            query=query,
            query_embedding=query_embedding,
            times_cooked_sq=times_cooked_sq,
            cuisine=cuisine,
            difficulty=difficulty,
            max_cook_time=max_cook_time,
            min_times_cooked=min_times_cooked,
            sort_by=sort_by,
            max_results=max_results,
            cte_limit=cte_limit,
            rrf_k=rrf_k,
        )

        full_payload_by_id = await _load_full_recipes(
            ctx=ctx,
            recipes=[item["recipe"] for item in items],
        )

        return {
            "status": "ok",
            "query": query,
            "recipes_page_path": "/recipes",
            "meal_plan_page_path": "/meal-plan",
            "filters_applied": {
                "cuisine": cuisine,
                "difficulty": difficulty,
                "max_cook_time": max_cook_time,
                "min_times_cooked": min_times_cooked,
            },
            "total_results": len(items),
            "recipes": [
                {
                    "id": str(item["recipe"].id),
                    "title": item["recipe"].name,
                    "detail_path": f"/recipes/{item['recipe'].id}",
                    "edit_path": f"/recipes/{item['recipe'].id}/edit",
                    "full_recipe": full_payload_by_id.get(str(item["recipe"].id)),
                    "times_cooked": item["times_cooked"],
                    "relevance_score": round(
                        _rrf_score(
                            text_rank=item["text_rank"],
                            vector_rank=item["vector_rank"],
                            k=rrf_k,
                        ),
                        4,
                    ),
                }
                for item in items
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

        full_payload_by_id = await _load_full_recipes(
            ctx=ctx,
            recipes=[recipe for recipe, _times_cooked in rows],
        )

        return {
            "status": "ok",
            "query": None,
            "recipes_page_path": "/recipes",
            "meal_plan_page_path": "/meal-plan",
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
                    "title": recipe.name,
                    "detail_path": f"/recipes/{recipe.id}",
                    "edit_path": f"/recipes/{recipe.id}/edit",
                    "full_recipe": full_payload_by_id.get(str(recipe.id)),
                    "times_cooked": times_cooked,
                }
                for recipe, times_cooked in rows
            ],
        }
