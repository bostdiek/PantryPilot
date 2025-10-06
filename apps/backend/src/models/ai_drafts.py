"""AI Draft model for temporary storage of AI-generated suggestions."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AIDraft(Base):
    """Model for temporary AI-generated content drafts.

    These are short-lived entities that store AI suggestions before user confirmation.
    Drafts expire automatically and are not part of the main application data model.
    """

    __tablename__ = "ai_drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of draft: recipe_suggestion, mealplan_suggestion, etc.",
    )
    payload: Mapped[Any] = mapped_column(
        JSON, nullable=False, comment="JSON payload containing the AI-generated content"
    )
    source_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Original URL if extracted from web content"
    )
    prompt_used: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="The prompt used for AI generation"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC) + timedelta(hours=1),
    )

    # Relationship to user (for convenience, though we enforce cascade)
    user = relationship("User", back_populates="ai_drafts")

    def __repr__(self) -> str:
        return f"<AIDraft(id={self.id}, type={self.type}, user_id={self.user_id})>"
