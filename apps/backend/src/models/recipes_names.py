from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base


class Recipe(Base):
    __tablename__ = "recipe_names"

    id = Column(Integer, primary_key=True, unique=True, nullable=False, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    prep_time = Column(Integer, nullable=False)
    cook_time = Column(Integer, nullable=False)
    total_time = Column(Integer, nullable=False)
    serving_min = Column(Integer, nullable=False)
    serving_max = Column(Integer, nullable=False)
    ethnicity = Column(String(255), nullable=False)
    course_type = Column(String(255), nullable=False)
    instructions = Column(Text, nullable=False)
    user_notes = Column(Text, nullable=False)
    ai_summary = Column(Text, nullable=False)
    link_source = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipeingredients = relationship("RecipeIngredient", back_populates="recipe")
