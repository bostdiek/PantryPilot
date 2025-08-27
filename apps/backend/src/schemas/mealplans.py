from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MealEntryIn(BaseModel):
    """Input model for creating/updating a meal entry in the weekly plan."""

    planned_for_date: Annotated[
        date, Field(description="Date the entry is planned for")
    ]
    recipe_id: UUID | None = Field(
        default=None, description="Recipe identifier; optional for leftovers/eating out"
    )
    meal_type: Literal["dinner"] = Field(default="dinner", description="Meal type")
    is_leftover: bool = Field(default=False, description="Mark as leftover entry")
    is_eating_out: bool = Field(default=False, description="Mark as eating out entry")
    notes: str | None = Field(default=None, description="Optional notes")
    order_index: int | None = Field(
        default=None,
        ge=0,
        description="Display order within the day (0-based). Defaults to end of list.",
    )

    model_config = ConfigDict(extra="forbid")


class MealEntryOut(MealEntryIn):
    """Output model for a meal entry, including DB identifiers and cooked info."""

    id: Annotated[UUID, Field(description="Unique identifier for the meal entry")]
    was_cooked: bool = Field(default=False, description="Whether the meal was cooked")
    cooked_at: datetime | None = Field(
        default=None, description="Timestamp when the meal was cooked, if any"
    )


class MealEntryPatch(BaseModel):
    """Partial update model for a meal entry.

    Includes all fields from MealEntryIn as optional, plus cooked fields.
    """

    planned_for_date: date | None = None
    recipe_id: UUID | None = None
    meal_type: Literal["dinner"] | None = None
    is_leftover: bool | None = None
    is_eating_out: bool | None = None
    notes: str | None = None
    order_index: int | None = Field(default=None, ge=0)
    was_cooked: bool | None = None
    cooked_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class MarkCookedIn(BaseModel):
    cooked_at: datetime | None = Field(
        default=None, description="Optional cooked timestamp; defaults to now"
    )


class DayPlanOut(BaseModel):
    """A single day's plan with ordered entries."""

    day_of_week: Annotated[
        Literal[
            "Sunday",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
        ],
        Field(description="Day of the week label"),
    ]
    date: Annotated[date, Field(description="ISO date for the day")]
    entries: list[MealEntryOut]


class WeeklyMealPlanOut(BaseModel):
    """Weekly container starting on Sunday with seven DayPlan entries."""

    week_start_date: Annotated[
        date, Field(description="Sunday start date for the week")
    ]
    days: list[DayPlanOut]
