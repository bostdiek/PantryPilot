"""Tool for retrieving meal plan history for pattern analysis."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from pydantic_ai import RunContext
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from models.meal_history import Meal
from services.chat_agent.deps import ChatAgentDeps
from services.chat_agent.schemas import MealPlanHistoryResponse, TimelineDayMeals


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
    - Meal rotation patterns to help users avoid ruts

    Args:
        days: Number of past days to retrieve (default: 28, max: 90)
              Timeline shows up to 30 days for monthly pattern analysis

    Returns:
        Structured meal history with chronological timeline (up to 30 days),
        top recipes, cuisine counts, and eating out/leftover statistics
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

    # Count recipe frequencies for top recipes
    recipe_counts: dict[str, int] = {}
    for meal in meals:
        if meal.recipe:
            recipe_name = meal.recipe.name
            recipe_counts[recipe_name] = recipe_counts.get(recipe_name, 0) + 1

    # Get top 10 most common recipes
    most_common_recipes = sorted(
        recipe_counts.items(), key=lambda x: x[1], reverse=True
    )[:10]

    # Count cuisines/ethnicities
    cuisine_counts: dict[str, int] = {}
    for meal in meals:
        if meal.recipe and meal.recipe.ethnicity:
            cuisine = meal.recipe.ethnicity
            cuisine_counts[cuisine] = cuisine_counts.get(cuisine, 0) + 1

    # Build chronological timeline for sequence analysis
    # Show full requested period (up to 30 days) for pattern analysis
    timeline_start_date = date.today() - timedelta(days=min(days, 30))

    # Group meals by date
    meals_by_date: dict[str, list[str]] = defaultdict(list)
    for meal in sorted(meals, key=lambda m: (m.planned_for_date, m.order_index)):
        # Only include meals within timeline window (up to 30 days for monthly patterns)
        if meal.planned_for_date < timeline_start_date:
            continue

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
        chronological_timeline=chronological_timeline,
        eating_out_count=sum(1 for m in meals if m.is_eating_out),
        leftover_count=sum(1 for m in meals if m.is_leftover),
        most_common_recipes=most_common_recipes,
        cuisine_counts=cuisine_counts,
    )
