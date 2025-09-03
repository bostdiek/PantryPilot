import uuid

from sqlalchemy import UUID, CheckConstraint, Column, DateTime, String, func
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Match schemas: username length 3–50
        # Use length(), which is SQLite/Postgres compatible
        CheckConstraint(
            "length(username) BETWEEN 3 AND 50", name="ck_users_username_len"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    meal = relationship("Meal", back_populates="user")
