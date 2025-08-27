from datetime import datetime
from enum import Enum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecipeDifficulty(str, Enum):
    """Difficulty level of the recipe."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class RecipeCategory(str, Enum):
    """Recipe category type."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    DESSERT = "dessert"
    SNACK = "snack"
    APPETIZER = "appetizer"


class IngredientPrepIn(BaseModel):
    """Optional preparation details for an ingredient."""

    method: str | None = Field(
        default=None, description="Preparation method, e.g. 'chopped'"
    )
    size_descriptor: str | None = Field(
        default=None, description="Size descriptor, e.g. 'diced', 'large'"
    )

    model_config = ConfigDict(extra="forbid")


class IngredientBase(BaseModel):
    """Base schema for ingredient input and output shapes."""

    name: Annotated[str, Field(min_length=1, description="Ingredient name")]
    quantity_value: float | None = Field(
        default=None, ge=0, description="Numeric quantity (non-negative)"
    )
    quantity_unit: str | None = Field(
        default=None, description="Unit for quantity (e.g., 'g', 'cup', 'tsp')"
    )
    prep: IngredientPrepIn | None = Field(
        default=None, description="Optional preparation details"
    )
    is_optional: bool = Field(
        default=False, description="Whether the ingredient is optional"
    )

    model_config = ConfigDict(extra="forbid")


class IngredientIn(IngredientBase):
    """Request model for creating/updating an ingredient."""

    pass


class IngredientOut(IngredientBase):
    """Response model including database identifier."""

    id: Annotated[UUID, Field(description="Unique identifier for the ingredient")]


class RecipeBase(BaseModel):
    """Base schema for recipe models."""

    title: Annotated[
        str, Field(min_length=1, max_length=255, description="Recipe title")
    ]
    description: str | None = Field(
        default=None, max_length=2000, description="Recipe description"
    )
    prep_time_minutes: Annotated[
        int, Field(ge=0, description="Preparation time in minutes")
    ]
    cook_time_minutes: Annotated[
        int, Field(ge=0, description="Cooking time in minutes")
    ]
    serving_min: Annotated[int, Field(ge=1, description="Minimum number of servings")]
    serving_max: int | None = Field(
        default=None, ge=1, description="Maximum number of servings"
    )
    instructions: Annotated[
        list[str], Field(min_length=1, description="Step-by-step instructions")
    ]
    difficulty: RecipeDifficulty = Field(
        default=RecipeDifficulty.MEDIUM, description="Recipe difficulty level"
    )
    category: Annotated[
        RecipeCategory, Field(description="Recipe category (breakfast, lunch, etc.)")
    ]
    ethnicity: str | None = Field(
        default=None, description="Cuisine ethnicity or origin"
    )
    oven_temperature_f: int | None = Field(
        default=None,
        ge=0,
        le=550,
        description="Oven temperature in Fahrenheit, if applicable",
    )
    user_notes: str | None = Field(
        default=None, max_length=1000, description="User notes about the recipe"
    )
    link_source: str | None = Field(
        default=None, max_length=255, description="Original source link, if applicable"
    )

    model_config = ConfigDict(extra="forbid")

    @staticmethod
    def _validate_serving_max_value(v: int | None, values: Any) -> int | None:
        """Shared validator ensuring serving_max >= serving_min when provided."""
        if v is None:
            return v
        min_val = values.data.get("serving_min") if hasattr(values, "data") else None
        if min_val is not None and v < min_val:
            raise ValueError(
                "Maximum servings must be greater than or equal to minimum servings"
            )
        return v

    @field_validator("serving_max")
    def validate_serving_max(cls, v: int | None, values: Any) -> int | None:  # noqa: D417
        return cls._validate_serving_max_value(v, values)


class RecipeCreate(RecipeBase):
    """Request model for creating a recipe."""

    ingredients: Annotated[
        list[IngredientIn], Field(min_length=1, description="Recipe ingredients")
    ]


class RecipeUpdate(BaseModel):
    """Request model for updating a recipe."""

    title: str | None = Field(
        default=None, min_length=1, max_length=255, description="Recipe title"
    )
    description: str | None = Field(
        default=None, max_length=2000, description="Recipe description"
    )
    prep_time_minutes: int | None = Field(
        default=None, ge=0, description="Preparation time in minutes"
    )
    cook_time_minutes: int | None = Field(
        default=None, ge=0, description="Cooking time in minutes"
    )
    serving_min: int | None = Field(
        default=None, ge=1, description="Minimum number of servings"
    )
    serving_max: int | None = Field(
        default=None, ge=1, description="Maximum number of servings"
    )
    instructions: Annotated[
        list[str] | None, Field(min_length=1, description="Step-by-step instructions")
    ] = None
    difficulty: RecipeDifficulty | None = Field(
        default=None, description="Recipe difficulty level"
    )
    category: RecipeCategory | None = Field(
        default=None, description="Recipe category (breakfast, lunch, etc.)"
    )
    ethnicity: str | None = Field(
        default=None, description="Cuisine ethnicity or origin"
    )
    oven_temperature_f: int | None = Field(
        default=None,
        ge=0,
        le=550,
        description="Oven temperature in Fahrenheit, if applicable",
    )
    user_notes: str | None = Field(
        default=None, max_length=1000, description="User notes about the recipe"
    )
    link_source: str | None = Field(
        default=None, max_length=255, description="Original source link, if applicable"
    )
    ingredients: list[IngredientIn] | None = Field(
        default=None, description="Recipe ingredients"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("serving_max")
    def validate_serving_max(cls, v: int | None, values: Any) -> int | None:  # noqa: D417
        return RecipeBase._validate_serving_max_value(v, values)


class RecipeOut(RecipeBase):
    """Response model for a recipe."""

    id: Annotated[UUID, Field(description="Unique identifier for the recipe")]
    ingredients: Annotated[
        list[IngredientOut], Field(description="Recipe ingredients with IDs")
    ]
    created_at: Annotated[datetime, Field(description="Creation timestamp")]
    updated_at: Annotated[datetime, Field(description="Last update timestamp")]
    total_time_minutes: Annotated[
        int, Field(description="Total recipe time (prep + cook)")
    ]
    ai_summary: str | None = Field(
        default=None, description="AI-generated summary of the recipe"
    )

    model_config = ConfigDict(extra="forbid")
