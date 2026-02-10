"""Tool for proposing meal plan entries in chat."""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import RunContext

from services.chat_agent.deps import ChatAgentDeps


logger = logging.getLogger(__name__)


async def tool_propose_meal_for_day(
    ctx: RunContext[ChatAgentDeps],
    date: str,
    day_label: str,
    existing_recipe_id: str | None = None,
    existing_recipe_title: str | None = None,
    existing_recipe_image_url: str | None = None,
    existing_recipe_detail_path: str | None = None,
    new_recipe_title: str | None = None,
    new_recipe_source_url: str | None = None,
    new_recipe_description: str | None = None,
    is_leftover: bool = False,
    is_eating_out: bool = False,
    notes: str | None = None,
) -> dict[str, Any]:
    """Propose a meal plan entry for a specific day.

    Use this during meal planning conversations to present recipe options
    to the user. Creates an interactive proposal card with Accept/Reject
    buttons but does NOT automatically add to meal plan.

    The meal proposal card is automatically displayed to the user with
    Accept/Reject buttons - you don't need to include it in your response
    blocks.

    WORKFLOW: During weekly meal planning, after analyzing history and
    getting user agreement on a high-level plan, use this tool for each
    day to propose specific meals. The user can accept or reject.

    IMPORTANT: Only propose ONE option per day at a time.

    Args:
        date: ISO date string (YYYY-MM-DD) for the meal
        day_label: Human-friendly day name (e.g., "Monday", "Taco Tuesday")
        existing_recipe_id: UUID of recipe from user's collection
        existing_recipe_title: Title of existing recipe
        existing_recipe_image_url: Optional image URL for existing recipe
        existing_recipe_detail_path: Path to recipe detail page (e.g., "/recipes/uuid")
        new_recipe_title: Title of new recipe from web search
        new_recipe_source_url: Source URL for new recipe
        new_recipe_description: Brief description of new recipe
        is_leftover: True if this is a leftover day
        is_eating_out: True if planning to eat out
        notes: Optional context or reasoning for the proposal

    Returns:
        Dict with status, message, and meal_proposal data. The meal_proposal
        is automatically rendered to the user.
    """
    # Build proposal block based on recipe type
    proposal_block: dict[str, Any] = {
        "type": "meal_proposal",
        "date": date,
        "day_label": day_label,
        "proposal_id": f"{date}-proposal",
        "existing_recipe": None,
        "new_recipe": None,
        "is_leftover": is_leftover,
        "is_eating_out": is_eating_out,
        "notes": notes,
    }

    # Add existing recipe option if provided
    if existing_recipe_id and existing_recipe_title:
        proposal_block["existing_recipe"] = {
            "id": existing_recipe_id,
            "title": existing_recipe_title,
            "image_url": existing_recipe_image_url,
            "detail_path": existing_recipe_detail_path,
        }

    # Add new recipe option if provided
    if new_recipe_title:
        proposal_block["new_recipe"] = {
            "title": new_recipe_title,
            "source_url": new_recipe_source_url,
            "description": new_recipe_description,
        }

    # Log proposal for debugging
    recipe_type = "existing" if existing_recipe_id else "new"
    recipe_name = existing_recipe_title or new_recipe_title or "leftover/eating out"
    logger.info(f"Proposing {recipe_type} meal for {day_label} ({date}): {recipe_name}")

    return {
        "status": "ok",
        "meal_proposal": proposal_block,
        "message": f"Proposed {recipe_name} for {day_label}",
    }
