from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from .meal_history import Meal

from .base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Match schemas: username length 3–50
        # Use length(), which is SQLite/Postgres compatible
        CheckConstraint(
            "length(username) BETWEEN 3 AND 50", name="ck_users_username_len"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    meal: Mapped[list[Meal]] = relationship("Meal", back_populates="user")
