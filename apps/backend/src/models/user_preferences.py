from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from .users import User

from .base import Base


class UserPreferences(Base):
    """User preferences for PantryPilot application."""
    
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        nullable=False, 
        index=True, 
        unique=True  # One preferences record per user
    )
    
    # Family and serving preferences
    family_size: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    default_servings: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    
    # Dietary restrictions and allergies (stored as JSON arrays)
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