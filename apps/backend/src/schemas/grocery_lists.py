"""Schemas for grocery list functionality."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GroceryListRequest(BaseModel):
    """Request model for generating a grocery list for a date range."""

    start_date: Annotated[
        date, Field(description="Start date for grocery list generation")
    ]
    end_date: Annotated[date, Field(description="End date for grocery list generation")]

    model_config = ConfigDict(extra="forbid")


class GroceryListIngredient(BaseModel):
    """Individual ingredient in a grocery list with aggregated quantity."""

    id: Annotated[UUID, Field(description="Ingredient identifier")]
    name: Annotated[str, Field(description="Ingredient name")]
    quantity_value: Annotated[
        float, Field(description="Total aggregated quantity across all recipes")
    ]
    quantity_unit: Annotated[str, Field(description="Unit for the quantity")]
    recipes: Annotated[
        list[str], Field(description="Names of recipes that use this ingredient")
    ]

    model_config = ConfigDict(extra="forbid")


class GroceryListResponse(BaseModel):
    """Response model for grocery list containing aggregated ingredients."""

    start_date: Annotated[date, Field(description="Start date of the grocery list")]
    end_date: Annotated[date, Field(description="End date of the grocery list")]
    ingredients: Annotated[
        list[GroceryListIngredient], Field(description="List of aggregated ingredients")
    ]
    total_meals: Annotated[
        int, Field(description="Total number of meals included in the date range")
    ]

    model_config = ConfigDict(extra="forbid")
