from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from .base import Base


class Meal(Base):
    __tablename__ = "meal_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipe_names.id"), nullable=False)
    date_suggested = Column(DateTime, nullable=False)
    week_suggested = Column(Integer, nullable=False)
    was_cooked = Column(Boolean, nullable=False)

    # Relationships
    user = relationship("User", back_populates="meal")
    recipe = relationship("Recipe", back_populates="meal")
