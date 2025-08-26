import uuid

from sqlalchemy import UUID, Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import relationship

from .base import Base


class Recipe(Base):
    __tablename__ = "recipe_names"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    prep_time_minutes = Column(Integer, nullable=True)
    cook_time_minutes = Column(Integer, nullable=True)
    total_time_minutes = Column(Integer, nullable=True)
    serving_min = Column(Integer, nullable=True)
    serving_max = Column(Integer, nullable=True)
    ethnicity = Column(String(255), nullable=True)
    course_type = Column(String(255), nullable=True)
    instructions = Column(Text, nullable=True)
    user_notes = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    link_source = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    recipeingredients = relationship("RecipeIngredient", back_populates="recipe")
