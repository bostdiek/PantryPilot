import uuid

from sqlalchemy import (
    UUID,
    Column,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from .base import Base


class Ingredient(Base):
    __tablename__ = "ingredient_names"
    __table_args__ = (
        # Unique constraint to prevent duplicate ingredient names per user
        # Note: NULL values in user_id are allowed and won't conflict
        UniqueConstraint("user_id", "ingredient_name", name="uq_ingredient_user_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )  # TODO: Make NOT NULL after migration
    ingredient_name = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    recipeingredients = relationship("RecipeIngredient", back_populates="ingredient")
    user = relationship("User", back_populates="ingredients")
