from pydantic import BaseModel, ConfigDict, Field


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

    name: str = Field(..., min_length=1, description="Ingredient name")
    quantity_value: float | None = Field(
        default=None, ge=0, description="Numeric quantity (non-negative)"
    )
    # NOTE: changed to str -- units are typically textual (g, cup, tsp, etc.)
    quantity_unit: str | None = Field(default=None, description="Unit for quantity")
    prep: IngredientPrepIn | None = Field(
        default=None, description="Optional preparation details"
    )
    is_optional: bool = Field(
        default=False, description="Whether the ingredient is optional"
    )

    model_config = ConfigDict(extra="forbid")


class IngredientsIn(IngredientBase):
    """Request model for creating/updating an ingredient."""


class IngredientsOut(IngredientBase):
    """Response model including database identifier."""

    id: str = Field(..., description="Unique identifier for the ingredient")
