from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


if TYPE_CHECKING:  # pragma: no cover
    from .chat_conversations import ChatConversation
    from .chat_messages import ChatMessage
    from .users import User


class ChatPendingAction(Base):
    __tablename__ = "chat_pending_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Assistant message that proposed this action (best-effort)",
    )

    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Tool/action identifier (app-defined)",
    )
    arguments: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=sa.text("'{}'::jsonb"),
        comment="Tool call arguments (JSON-serializable)",
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Short user-visible title describing the proposed action",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="User-visible description of what will happen",
    )
    confirm_label: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        server_default=sa.text("'Apply'"),
        comment="UI label for the accept button",
    )
    cancel_label: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        server_default=sa.text("'Cancel'"),
        comment="UI label for the cancel button",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=sa.text("'proposed'"),
        comment="proposed|accepted|canceled|succeeded|failed",
    )
    cancel_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional user-provided cancellation reason",
    )

    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Tool result payload (when succeeded)",
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if execution failed",
    )

    action_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sa.text("'{}'::jsonb"),
        comment="Non-LLM metadata for UI/provenance",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the user accepted the proposal",
    )
    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the user canceled the proposal",
    )
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the tool execution completed (success or failure)",
    )

    conversation: Mapped[ChatConversation] = relationship(
        "ChatConversation", back_populates="pending_actions"
    )
    user: Mapped[User] = relationship("User", back_populates="chat_pending_actions")
    message: Mapped[ChatMessage | None] = relationship("ChatMessage")
