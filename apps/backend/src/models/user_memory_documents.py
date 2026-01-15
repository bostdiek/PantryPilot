"""User memory document model for persistent assistant memory."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


if TYPE_CHECKING:
    from .users import User


class UserMemoryDocument(Base):
    """Single per-user memory document maintained by the assistant.

    The assistant updates this document automatically when it detects
    preferences, constraints, or other memorable information. Users can
    view and edit this document directly in their account settings.
    """

    __tablename__ = "user_memory_documents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=sa.text("''"),
        comment="Markdown-formatted memory content",
    )

    format: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=sa.text("'markdown'"),
        comment="Content format (currently only 'markdown' supported)",
    )

    version: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("1"),
        comment="Version counter incremented on each update",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        comment="Last update timestamp",
    )

    updated_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=sa.text("'assistant'"),
        comment="Who made the last update: 'assistant' or 'user'",
    )

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
        comment="Additional metadata (e.g., update triggers, source messages)",
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="memory_document")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "format IN ('markdown')",
            name="ck_user_memory_documents_format_valid",
        ),
        CheckConstraint(
            "updated_by IN ('assistant', 'user')",
            name="ck_user_memory_documents_updated_by_valid",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_user_memory_documents_version_positive",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<UserMemoryDocument(user_id={self.user_id}, "
            f"version={self.version}, updated_by={self.updated_by})>"
        )
