"""Schemas for chat tool proposals and results."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ToolProposal(BaseModel):
    proposal_id: UUID
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    title: str
    description: str
    confirm_label: str = "Apply"
    cancel_label: str = "Cancel"

    model_config = ConfigDict(extra="forbid")


class ToolResultEnvelope(BaseModel):
    proposal_id: UUID
    tool_name: str
    status: Literal["success", "error"]
    result: dict[str, Any] | None = None
    error: str | None = None

    model_config = ConfigDict(extra="forbid")


class ToolCancelRequest(BaseModel):
    reason: str | None = Field(
        default=None,
        max_length=400,
        description="Optional user-provided cancellation reason.",
    )

    model_config = ConfigDict(extra="forbid")


class ToolCancelResponse(BaseModel):
    proposal_id: UUID
    status: Literal["canceled"]
    cancel_reason: str | None = None

    model_config = ConfigDict(extra="forbid")
