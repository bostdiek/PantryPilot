import uuid

from sqlalchemy import UUID, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Recipe(Base):
    __tablename__ = "recipe_names"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )  # TODO: Make NOT NULL after migration
    name = Column(String(255), nullable=False, index=True)
    prep_time_minutes = Column(Integer, nullable=True)
    cook_time_minutes = Column(Integer, nullable=True)
    total_time_minutes = Column(Integer, nullable=True)
    serving_min = Column(Integer, nullable=True)
    serving_max = Column(Integer, nullable=True)
    ethnicity = Column(String(255), nullable=True)
    difficulty = Column(String(50), nullable=True)
    course_type = Column(String(255), nullable=True)
    # Stored as a Postgres TEXT[] (list of instruction steps)
    instructions: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    user_notes = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    link_source = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    recipeingredients = relationship("RecipeIngredient", back_populates="recipe")
    user = relationship("User")
