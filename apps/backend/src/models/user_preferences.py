from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, CheckConstraint, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column


if TYPE_CHECKING:  # pragma: no cover - only for type checking
    pass

from .base import Base


class UserPreferences(Base):
    """User preferences for PantryPilot application."""

    __tablename__ = "user_preferences"
    __table_args__ = (
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_user_preferences_latitude_valid",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_user_preferences_longitude_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        unique=True,  # One preferences record per user
    )

    # Family and serving preferences
    family_size: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    default_servings: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    # Dietary restrictions and allergies (stored as PostgreSQL text arrays)
    # Use callable default=list (SQLAlchemy invokes per row; avoids shared mutable)
    allergies: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    dietary_restrictions: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )

    # App preferences
    theme: Mapped[str] = mapped_column(String(20), nullable=False, default="light")
    units: Mapped[str] = mapped_column(String(20), nullable=False, default="imperial")

    # Meal planning preferences
    meal_planning_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    preferred_cuisines: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )

    # Location fields (for weather tool and meal planning context)
    # User-facing fields
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="User's city (for weather and meal planning)",
    )
    state_or_region: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="State/region/province (e.g., 'CA', 'Ontario')",
    )
    postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Postal/ZIP code",
    )
    country: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        server_default="'US'",
        comment="ISO 3166-1 alpha-2 country code (default US)",
    )

    # Internal geocoded fields (for weather API calls)
    latitude: Mapped[float | None] = mapped_column(
        Numeric(precision=9, scale=6),
        nullable=True,
        comment="Geocoded latitude (-90 to 90)",
    )
    longitude: Mapped[float | None] = mapped_column(
        Numeric(precision=9, scale=6),
        nullable=True,
        comment="Geocoded longitude (-180 to 180)",
    )
    timezone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="IANA timezone identifier (e.g., 'America/New_York')",
    )
    geocoded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last geocoding timestamp",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship - back to user (but no foreign key constraint for now)
    # We'll add the FK constraint in a migration after we're sure it works
    # user: Mapped[User] = relationship("User", back_populates="preferences")
