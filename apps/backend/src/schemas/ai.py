"""AI-related schemas for recipe extraction and suggestions."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from .recipes import RecipeCreate


class AIRecipeFromUrlRequest(BaseModel):
    """Request schema for extracting a recipe from a URL."""

    source_url: HttpUrl = Field(..., description="Recipe page URL to extract from")
    prompt_override: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional custom prompt to override default extraction prompt",
    )

    model_config = ConfigDict(extra="forbid")


class AIDraftResponse(BaseModel):
    """Response schema for AI draft creation with signed deep link."""

    draft_id: UUID = Field(..., description="Unique identifier for the draft")
    signed_url: str = Field(
        ..., description="Signed deep link URL for frontend to load the draft"
    )
    expires_at: datetime = Field(..., description="Expiration timestamp for the draft")
    ttl_seconds: int = Field(..., description="Time to live in seconds")

    model_config = ConfigDict(extra="forbid")


class AIDraftFetchResponse(BaseModel):
    """Response schema for fetching an AI draft payload."""

    payload: dict[str, Any] = Field(
        ..., description="Draft payload containing extracted recipe data"
    )
    type: Literal["recipe_suggestion"] = Field(
        ..., description="Type of the draft content"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: datetime = Field(..., description="Expiration timestamp")

    model_config = ConfigDict(extra="forbid")


class AIGeneratedRecipe(BaseModel):
    """AI-generated recipe data that follows RecipeCreate schema."""

    # Use RecipeCreate as base but add AI-specific metadata
    recipe_data: RecipeCreate = Field(
        ..., description="Generated recipe following standard schema"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="AI confidence in the extraction (0-1)"
    )
    extraction_notes: str | None = Field(
        default=None, description="Notes about the extraction process or issues"
    )
    source_url: str = Field(
        ..., description="Original URL the recipe was extracted from"
    )

    model_config = ConfigDict(extra="forbid")
