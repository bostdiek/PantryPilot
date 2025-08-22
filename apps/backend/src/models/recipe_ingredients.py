import uuid
from datetime import datetime

from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import Base


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    recipe_id = Column(
        UUID(as_uuid=True), ForeignKey("recipe_names.id"), nullable=False
    )
    ingredient_id = Column(
        UUID(as_uuid=True), ForeignKey("ingredient_names.id"), nullable=False
    )  # noqa: E501
    quantity = Column(String(255), nullable=False)
    unit = Column(String(255), nullable=False)
    is_optional = Column(Boolean, default=False)
    user_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipe = relationship("Recipe", back_populates="recipeingredients")
    ingredient = relationship("Ingredient", back_populates="recipeingredients")
