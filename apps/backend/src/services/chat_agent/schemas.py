"""Pydantic models for chat agent tool outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MealEntry(BaseModel):
    """Individual meal entry with metadata for pattern analysis."""

    date: str = Field(description="ISO date string (YYYY-MM-DD)")
    meal_type: str = Field(description="breakfast, lunch, dinner, or snack")
    recipe_name: str | None = Field(
        description="Recipe name if planned, null for eating out or leftover"
    )
    is_eating_out: bool = Field(description="Whether this was eating at a restaurant")
    is_leftover: bool = Field(
        description="Whether this was leftover from previous meal"
    )
    was_cooked: bool = Field(
        description="Whether this recipe was actually cooked (may be unreliable)"
    )
    notes: str | None = Field(description="User notes about this meal")


class DayOfWeekMeals(BaseModel):
    """Meals grouped by day of week for pattern detection."""

    day_name: str = Field(description="Day of week (Monday, Tuesday, etc.)")
    meals: list[MealEntry] = Field(
        description="All meals planned for this day across the time period"
    )


class TimelineDayMeals(BaseModel):
    """Meals for a specific date in chronological order."""

    date: str = Field(description="ISO date string (YYYY-MM-DD)")
    meals: list[str] = Field(
        description="Recipe names or labels (Eating Out, Leftover, etc.) for this date"
    )


class MealPlanHistoryResponse(BaseModel):
    """Optimized meal history focused on summary stats and recent patterns."""

    status: str = Field(default="ok")
    days_analyzed: int = Field(description="Number of days included in analysis")
    total_meals: int = Field(description="Total meal count across all days")
    chronological_timeline: list[TimelineDayMeals] = Field(
        description=(
            "Date-ordered list showing what was planned each day (up to 30 days) - "
            "useful for analyzing patterns, sequences, and helping users "
            "avoid meal ruts"
        )
    )
    eating_out_count: int = Field(
        description="Total times eating out during this period"
    )
    leftover_count: int = Field(description="Total leftover meals during this period")
    most_common_recipes: list[tuple[str, int]] = Field(
        default_factory=list,
        description="Top recipes by frequency [(recipe_name, count), ...]",
    )
    cuisine_counts: dict[str, int] = Field(
        description=(
            "Frequency of each cuisine type (Italian: 5, Mexican: 3, etc.) "
            "to assess variety"
        )
    )
