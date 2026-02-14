"""Schemas for AI training samples."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrainingSampleCreate(BaseModel):
    """Data required to create a training sample."""

    conversation_id: UUID
    message_id: UUID
    user_id: UUID
    raw_prompt: str = Field(..., description="Full prompt sent to LLM")
    raw_response: str = Field(..., description="Raw LLM output")
    tool_calls: dict[str, Any] | None = Field(
        default=None, description="Tool calls in this turn"
    )
    model_name: str = Field(..., description="LLM model identifier")
    model_version: str | None = Field(default=None, description="Model version")
    temperature: float | None = Field(default=None, description="Temperature parameter")
    max_tokens: int | None = Field(default=None, description="Max tokens parameter")
    prompt_tokens: int | None = Field(default=None, description="Input token count")
    completion_tokens: int | None = Field(
        default=None, description="Output token count"
    )
    latency_ms: int | None = Field(
        default=None, description="Response time in milliseconds"
    )
    is_simulated: bool = Field(
        default=False, description="True if synthetic data, False if real user"
    )

    model_config = ConfigDict(extra="forbid")


class TrainingSampleResponse(BaseModel):
    """Training sample data returned from API."""

    id: UUID
    conversation_id: UUID
    message_id: UUID
    user_id: UUID
    model_name: str
    model_version: str | None
    user_feedback: Literal["positive", "negative"] | None
    is_simulated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class TrainingSampleFeedback(BaseModel):
    """User feedback for a training sample."""

    user_feedback: Literal["positive", "negative"] = Field(
        ..., description="User rating for the response quality"
    )

    model_config = ConfigDict(extra="forbid")
