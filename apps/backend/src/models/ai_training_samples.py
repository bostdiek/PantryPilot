"""AI Training Samples model for storing LLM interactions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


if TYPE_CHECKING:  # pragma: no cover
    from .chat_conversations import ChatConversation
    from .chat_messages import ChatMessage
    from .users import User


class AITrainingSample(Base):
    """Stores raw LLM interactions for fine-tuning.

    Retention: 1 year (separate from operational chat data).
    """

    __tablename__ = "ai_training_samples"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Raw LLM interaction
    raw_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full prompt sent to LLM including system messages and context",
    )
    raw_response: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Raw LLM output before parsing"
    )

    # Tool calling data
    tool_calls: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Dictionary of tool calls by call_id for training format",
    )

    # LLM metadata
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="LLM model identifier"
    )
    model_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Model version if available"
    )
    temperature: Mapped[float | None] = mapped_column(
        nullable=True, comment="Temperature parameter used"
    )
    max_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Max tokens parameter used"
    )

    # Performance metrics
    prompt_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Token count for input"
    )
    completion_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Token count for output"
    )
    latency_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Total response time in milliseconds"
    )

    # Quality signals
    user_feedback: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="User rating: positive|negative",
    )
    is_simulated: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=sa.text("false"),
        comment="True if from synthetic data generation, False if real user",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_training_samples_created_at", "created_at"),
        Index("ix_training_samples_conversation_id", "conversation_id"),
        Index("ix_training_samples_feedback", "user_feedback"),
        Index("ix_training_samples_message_user", "message_id", "user_id"),
    )

    # Relationships
    conversation: Mapped[ChatConversation] = relationship(
        "ChatConversation",
        foreign_keys=[conversation_id],
        back_populates="training_samples",
    )
    message: Mapped[ChatMessage] = relationship(
        "ChatMessage", foreign_keys=[message_id]
    )
    user: Mapped[User] = relationship("User", foreign_keys=[user_id])
