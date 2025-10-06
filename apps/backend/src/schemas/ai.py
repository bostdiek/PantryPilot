"""AI-related schemas for recipe extraction and suggestions.

This module defines the structured Pydantic models used by the AI agent and
the API layers. It includes models for successful extraction as well as
structured failure outputs the agent can return (see Pydantic AI output
functions documentation for the pattern).
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from .recipes import RecipeCreate


class ExtractionNotFound(BaseModel):
    """Agent output: no extractable recipe was found on the page.

    This is intended to be registered as one of the agent `output_type`
    alternatives (a simple Pydantic model with a single `reason` field).
    """

    reason: str = Field(..., description="Why extraction failed (e.g. no recipe found)")

    model_config = ConfigDict(extra="forbid")


class ExtractionFailureResponse(BaseModel):
    """Requester-facing output describing an extraction failure.

    This is the schema the API (or router agents) can use when returning
    a structured failure back to the caller. It includes the attempted URL
    and optional details to aid debugging or display.
    """

    reason: str = Field(..., description="Why extraction failed (e.g. no recipe found)")
    source_url: str = Field(..., description="URL attempted for extraction")
    details: dict[str, Any] | None = Field(
        default=None, description="Optional extra details about the failure"
    )

    model_config = ConfigDict(extra="forbid")


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


class RecipeExtractionResult(RecipeCreate):
    """Result from AI recipe extraction, extends RecipeCreate with AI metadata."""

    confidence_score: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="AI confidence in the extraction (0-1)",
    )
    extraction_notes: str | None = Field(
        default=None, description="Notes about the extraction process or issues"
    )
    # Optionally override link_source for extraction
    link_source: str | None = Field(
        default=None,
        max_length=255,
        description="Original source link, if applicable",
    )


class SSEEvent(BaseModel):
    """Structured Server-Sent Event payload for extraction streaming.

    Centralizes schema for all SSE messages so the orchestrator cannot drift.
    Fields are optional except `status` and `step`. The `to_sse` helper renders
    the wire format. Terminal helpers produce standardized final events.
    """

    status: str = Field(
        ..., description="High-level event type e.g. started, error, complete"
    )
    step: str = Field(..., description="Pipeline step identifier")
    progress: float | None = Field(
        None, ge=0.0, le=1.0, description="Fractional progress (0.0–1.0)"
    )
    detail: str | None = Field(
        None, description="Optional human-readable detail or error message"
    )
    draft_id: Any | None = Field(
        None, description="Draft identifier when available (UUID)"
    )
    success: bool | None = Field(
        None, description="Final success indicator for terminal events"
    )
    error_code: str | None = Field(
        None, description="Stable machine readable error code for analytics"
    )

    def to_sse(self) -> str:  # pragma: no cover - trivial
        return f"data: {self.model_dump_json()}\n\n"

    @classmethod
    def terminal_success(cls, draft_id: Any, success: bool) -> "SSEEvent":  # noqa: D401
        # Use model_validate to avoid mypy/Pydantic __init__ positional/keyword
        # signature issues when instantiating the model in typed contexts.
        return cls.model_validate(
            {
                "status": "complete",
                "step": "complete",
                "draft_id": draft_id,
                "success": success,
                "progress": 1.0,
            }
        )

    @classmethod
    def terminal_error(
        cls, step: str, detail: str, error_code: str | None = None
    ) -> "SSEEvent":  # noqa: D401
        # Use model_validate to avoid mypy/Pydantic __init__ positional/keyword
        # signature issues when instantiating the model in typed contexts.
        return cls.model_validate(
            {
                "status": "error",
                "step": step,
                "detail": detail,
                "error_code": error_code,
                "progress": 1.0,
                "success": False,
            }
        )
