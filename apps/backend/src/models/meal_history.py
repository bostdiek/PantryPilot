import uuid
from datetime import date, datetime

from sqlalchemy import (
    UUID,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Meal(Base):
    __tablename__ = "meal_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipe_names.id"), nullable=True
    )
    date_suggested: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    week_suggested: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Planning fields
    planned_for_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(50), nullable=False, default="dinner")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_leftover: Mapped[bool | None] = mapped_column(Boolean, server_default="false")
    is_eating_out: Mapped[bool | None] = mapped_column(Boolean, server_default="false")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cooked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    was_cooked: Mapped[bool | None] = mapped_column(Boolean, server_default="false")

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="meal")
    recipe = relationship("Recipe")
