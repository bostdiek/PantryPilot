from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base


class RecipeIngredients(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, unique=True, nullable=False, index=True)
    recipe_id = Column(Integer, ForeignKey("recipe_names.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredient_names.id"), nullable=False)
    quantity = Column(String(255), nullable=False)
    unit = Column(String(255), nullable=False)
    user_notes = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipe = relationship("Recipe", back_populates="recipeingredients")
    ingredient = relationship("Ingredients", back_populates="recipeingredients")
