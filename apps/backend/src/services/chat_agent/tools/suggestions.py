"""Tool for suggesting recipes and creating drafts."""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import RunContext

from core.security import create_draft_token
from dependencies.db import AsyncSessionLocal
from services.ai.draft_service import create_success_draft
from services.chat_agent.deps import ChatAgentDeps


logger = logging.getLogger(__name__)


async def tool_suggest_recipe(
    ctx: RunContext[ChatAgentDeps],
    title: str,
    description: str,
    prep_time_minutes: int,
    cook_time_minutes: int,
    serving_min: int,
    instructions: list[str],
    category: str,
    ingredients: list[dict[str, Any]],
    source_url: str | None = None,
) -> dict[str, Any]:
    """Suggest a recipe to the user and create a draft for approval.

    Use this when the user asks for recipe suggestions or when you find
    a recipe they might like. Creates a draft that the user can review
    and add to their collection.

    The recipe card is automatically displayed to the user with an "Add Recipe"
    button - you don't need to include it in your response blocks.

    WORKFLOW: After using fetch_url_as_markdown to read a recipe page,
    extract the recipe details and call this tool to create a saveable
    draft.

    Args:
        title: Recipe title
        description: Brief description of the dish
        prep_time_minutes: Preparation time in minutes
        cook_time_minutes: Cooking time in minutes
        serving_min: Minimum number of servings
        instructions: List of cooking instruction steps (each step as a string)
        category: Recipe category - one of: breakfast, lunch, dinner,
                  dessert, snack, appetizer
        ingredients: List of ingredient objects, each with:
            - name (str, required): Ingredient name
            - quantity_value (float, optional): Amount
            - quantity_unit (str, optional): Unit (cups, tbsp, etc.)
            - is_optional (bool, optional): Whether optional
        source_url: Original recipe URL if from external source

    Returns:
        Dict with status, message, and recipe_card data. The recipe_card
        is automatically rendered to the user.
    """
    user = ctx.deps.user

    # Build recipe payload
    recipe_data = {
        "title": title,
        "description": description,
        "prep_time_minutes": prep_time_minutes,
        "cook_time_minutes": cook_time_minutes,
        "serving_min": serving_min,
        "instructions": instructions,
        "category": category,
        "ingredients": ingredients,
        "difficulty": "medium",
    }

    if source_url:
        recipe_data["link_source"] = source_url

    try:
        # Use a separate database session for draft creation to avoid
        # conflicts with concurrent tool executions (pydantic-ai runs
        # multiple tools in parallel, which can cause session conflicts)
        async with AsyncSessionLocal() as draft_db:
            draft = await create_success_draft(
                db=draft_db,
                current_user=user,
                source_url=source_url or "chat://recommendation",
                generated_recipe=recipe_data,
            )
            # Commit the draft in this separate session
            await draft_db.commit()

        # Generate signed token for secure access
        token = create_draft_token(draft_id=draft.id, user_id=user.id)

        # Build deep-link URL
        deep_link = f"/recipes/new?ai=1&draftId={draft.id}&token={token}"

        return {
            "status": "ok",
            "recipe_card": {
                "type": "recipe_card",
                "title": title,
                "subtitle": description,
                "image_url": None,
                "href": deep_link,
                "source_url": source_url,  # Original external URL for "View Recipe"
            },
            "message": (
                f"Created recipe draft for '{title}'. "
                "User can click 'Add Recipe' to save it."
            ),
        }

    except Exception as e:
        logger.error(f"Failed to create recipe draft: {e}")
        return {
            "status": "error",
            "recipe_card": None,
            "message": f"Failed to create recipe draft: {e!s}",
        }
