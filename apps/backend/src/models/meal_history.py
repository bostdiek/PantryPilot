import uuid

from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from .base import Base


class Meal(Base):
    __tablename__ = "meal_history"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipe_names.id"), nullable=True)
    date_suggested = Column(DateTime(timezone=True), nullable=True)
    week_suggested = Column(Integer, nullable=True)
    # Planning fields
    planned_for_date = Column(Date, nullable=False)
    meal_type = Column(String(50), nullable=False, default="dinner")
    order_index = Column(Integer, nullable=False, default=0)
    is_leftover = Column(Boolean, server_default="false")
    is_eating_out = Column(Boolean, server_default="false")
    notes = Column(Text, nullable=True)
    cooked_at = Column(DateTime(timezone=True), nullable=True)
    was_cooked = Column(Boolean, server_default="false")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="meal")
    recipe = relationship("Recipe")
