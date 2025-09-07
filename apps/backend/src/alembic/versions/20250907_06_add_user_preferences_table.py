"""add user preferences table

Revision ID: 20250907_06
Revises: 20250905_05
Create Date: 2025-09-07

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from alembic import op


# revision identifiers, used by Alembic.
revision = "20250907_06"
down_revision = "20250905_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_preferences table
    op.create_table(
        "user_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, unique=True),
        # Family and serving preferences
        sa.Column("family_size", sa.Integer(), nullable=False, default=2),
        sa.Column("default_servings", sa.Integer(), nullable=False, default=4),
        # Dietary restrictions and allergies
        sa.Column("allergies", ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column("dietary_restrictions", ARRAY(sa.String()), nullable=False, default=[]),
        # App preferences
        sa.Column("theme", sa.String(20), nullable=False, default="light"),
        sa.Column("units", sa.String(20), nullable=False, default="imperial"),
        # Meal planning preferences
        sa.Column("meal_planning_days", sa.Integer(), nullable=False, default=7),
        sa.Column("preferred_cuisines", ARRAY(sa.String()), nullable=False, default=[]),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    
    # Create indexes
    op.create_index("ix_user_preferences_id", "user_preferences", ["id"])
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"])
    
    # Add foreign key constraint to users table
    # For now, we'll skip this to avoid circular dependency issues
    # op.create_foreign_key(
    #     "fk_user_preferences_user_id",
    #     "user_preferences",
    #     "users",
    #     ["user_id"],
    #     ["id"],
    #     ondelete="CASCADE",
    # )


def downgrade() -> None:
    # Drop foreign key constraint first (if it exists)
    # op.drop_constraint("fk_user_preferences_user_id", "user_preferences", type_="foreignkey")
    
    # Drop indexes
    op.drop_index("ix_user_preferences_user_id")
    op.drop_index("ix_user_preferences_id")
    
    # Drop table
    op.drop_table("user_preferences")