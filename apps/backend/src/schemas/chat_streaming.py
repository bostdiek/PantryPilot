"""Schemas for chat assistant SSE streaming."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


MAX_SSE_EVENT_BYTES: int = 16_384


class ChatSseEvent(BaseModel):
    """Canonical SSE envelope for chat assistant streaming.

    Keep payloads small (no large HTML or scraped content). Use blocks for
    structured data instead of raw payload dumps.
    """

    event: Literal[
        "status",
        "message.delta",
        "message.complete",
        "blocks.append",
        "tool.started",
        "tool.proposed",
        "tool.canceled",
        "tool.result",
        "memory.updated",
        "summary.updated",
        "error",
        "done",
    ]
    conversation_id: UUID
    message_id: UUID | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    def to_sse(self) -> str:
        """Serialize event to SSE format with size validation."""
        payload = self.model_dump_json()
        if len(payload.encode("utf-8")) > MAX_SSE_EVENT_BYTES:
            raise ValueError(
                "SSE payload exceeded MAX_SSE_EVENT_BYTES; avoid large HTML or "
                "scraped content."
            )
        return f"data: {payload}\n\n"


class ChatStreamRequest(BaseModel):
    """Request payload for streaming a chat assistant response."""

    content: str = Field(..., min_length=1, max_length=4000)
    client_context: dict[str, Any] | None = Field(
        default=None,
        description="Optional client context for routing/experiments.",
    )

    model_config = ConfigDict(extra="forbid")


# -----------------------------------------------------------------------------
# Conversation History Response Schemas
# -----------------------------------------------------------------------------


class ConversationSummary(BaseModel):
    """Summary of a chat conversation for list views."""

    id: UUID
    title: str | None = None
    created_at: str
    last_activity_at: str

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    """Response for listing user conversations."""

    conversations: list[ConversationSummary]
    total: int
    has_more: bool

    model_config = ConfigDict(extra="forbid")


class MessageSummary(BaseModel):
    """Summary of a chat message for history views."""

    id: UUID
    role: str
    content_blocks: list[dict[str, Any]]
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class MessageHistoryResponse(BaseModel):
    """Response for fetching message history."""

    messages: list[MessageSummary]
    has_more: bool

    model_config = ConfigDict(extra="forbid")
