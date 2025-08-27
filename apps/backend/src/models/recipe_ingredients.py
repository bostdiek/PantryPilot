import uuid

from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
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
    quantity_value = Column(Numeric, nullable=True)
    quantity_unit = Column(String(64), nullable=True)
    prep = Column(JSONB, nullable=False, server_default="{}")
    is_optional = Column(Boolean, default=False)
    user_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    recipe = relationship("Recipe", back_populates="recipeingredients")
    ingredient = relationship("Ingredient", back_populates="recipeingredients")
