import uuid

from sqlalchemy import UUID, Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import relationship

from .base import Base


class Ingredient(Base):
    __tablename__ = "ingredient_names"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )  # TODO: Make NOT NULL after migration
    ingredient_name = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    recipeingredients = relationship("RecipeIngredient", back_populates="ingredient")
    user = relationship("User")
