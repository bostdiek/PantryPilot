"""Tool for retrieving meal plan history for pattern analysis."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from pydantic_ai import RunContext
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from models.meal_history import Meal
from services.chat_agent.schemas import MealPlanHistoryResponse, TimelineDayMeals


if TYPE_CHECKING:
    from services.chat_agent.agent import ChatAgentDeps


async def tool_get_meal_plan_history(
    ctx: RunContext[ChatAgentDeps],
    days: int = 28,
) -> MealPlanHistoryResponse:
    """Get the user's meal plan history to analyze eating patterns.

    Use this to understand meal planning trends like:
    - Favorite days for specific meals (Taco Tuesday, Pizza Friday)
    - How often they eat out vs cook at home
    - Leftover usage patterns
    - Most frequently cooked recipes
    - Cuisine variety and preferences

    Args:
        days: Number of past days to retrieve (default: 28, max: 90)

    Returns:
        Structured meal history with chronological timeline, day-of-week
        patterns, cuisine counts, and eating out/leftover statistics
    """
    days = max(1, min(days, 90))  # Clamp to 1-90
    start_date = date.today() - timedelta(days=days)

    stmt = (
        select(Meal)
        .where(
            and_(
                Meal.user_id == ctx.deps.user.id,
                Meal.planned_for_date >= start_date,
            )
        )
        .options(selectinload(Meal.recipe))
        .order_by(Meal.planned_for_date.desc(), Meal.meal_type)
    )

    result = await ctx.deps.db.execute(stmt)
    meals = result.scalars().all()

    # Group by day of week for pattern analysis
    day_patterns: dict[str, list[dict[str, Any]]] = {}
    for meal in meals:
        day_name = meal.planned_for_date.strftime("%A")
        if day_name not in day_patterns:
            day_patterns[day_name] = []
        day_patterns[day_name].append(
            {
                "date": meal.planned_for_date.isoformat(),
                "meal_type": meal.meal_type,
                "recipe_name": meal.recipe.name if meal.recipe else None,
                "is_eating_out": meal.is_eating_out,
                "is_leftover": meal.is_leftover,
                "was_cooked": meal.was_cooked,
                "notes": meal.notes,
            }
        )

    # Count cuisines/ethnicities
    cuisine_counts: dict[str, int] = {}
    for meal in meals:
        if meal.recipe and meal.recipe.ethnicity:
            cuisine = meal.recipe.ethnicity
            cuisine_counts[cuisine] = cuisine_counts.get(cuisine, 0) + 1

    # Build chronological timeline for sequence analysis
    # Group meals by date
    meals_by_date: dict[str, list[str]] = defaultdict(list)
    for meal in sorted(meals, key=lambda m: (m.planned_for_date, m.order_index)):
        date_str = meal.planned_for_date.isoformat()
        if meal.recipe:
            recipe_label = meal.recipe.name
        elif meal.is_eating_out:
            recipe_label = "Eating Out"
        elif meal.is_leftover:
            recipe_label = f"Leftover{f': {meal.notes}' if meal.notes else ''}"
        else:
            recipe_label = meal.notes or "Unplanned"

        meals_by_date[date_str].append(recipe_label)

    # Convert to list for ordered display
    chronological_timeline = [
        TimelineDayMeals(date=date_str, meals=meals_list)
        for date_str, meals_list in sorted(meals_by_date.items(), reverse=True)
    ]

    return MealPlanHistoryResponse(
        days_analyzed=days,
        total_meals=len(meals),
        meals_by_day_of_week=day_patterns,
        chronological_timeline=chronological_timeline,
        eating_out_count=sum(1 for m in meals if m.is_eating_out),
        leftover_count=sum(1 for m in meals if m.is_leftover),
        cuisine_counts=cuisine_counts,
    )
