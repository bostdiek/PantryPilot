import uuid
from datetime import datetime

from sqlalchemy import UUID, Column, DateTime, String
from sqlalchemy.orm import relationship

from .base import Base


class Ingredient(Base):
    __tablename__ = "ingredient_names"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    ingredient_name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipeingredients = relationship("RecipeIngredient", back_populates="ingredients")
