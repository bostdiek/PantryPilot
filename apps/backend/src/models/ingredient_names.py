from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class Ingredient(Base):
    __tablename__ = "ingredient_names"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipeingredients = relationship("RecipeIngredient", back_populates="ingredients")
