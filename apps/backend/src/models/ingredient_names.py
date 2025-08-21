from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Ingredients(Base):
    __tablename__ = "ingredient_names"

    id = Column(Integer, primary_key=True, unique=True, nullable=False, index=True)
    ingredient_name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipeingredients = relationship("RecipeIngredient", back_populates="ingredients")
