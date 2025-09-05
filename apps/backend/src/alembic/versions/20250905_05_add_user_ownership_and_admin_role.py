"""add user ownership and admin role

Revision ID: 20250905_05
Revises: 20250902_04
Create Date: 2025-09-05

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op


# revision identifiers, used by Alembic.
revision = "20250905_05"
down_revision = "20250902_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_admin column to users table
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Add user_id foreign key to recipe_names table
    op.add_column(
        "recipe_names",
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),  # Nullable initially
    )
    op.create_foreign_key(
        "fk_recipe_names_user_id",
        "recipe_names",
        "users",
        ["user_id"],
        ["id"],
    )

    # Add user_id foreign key to ingredient_names table
    op.add_column(
        "ingredient_names",
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),  # Nullable initially
    )
    op.create_foreign_key(
        "fk_ingredient_names_user_id",
        "ingredient_names",
        "users",
        ["user_id"],
        ["id"],
    )

    # TODO: In production, you would need to:
    # 1. Populate user_id fields with actual user associations
    # 2. Change the columns to NOT NULL after population
    # For development/testing, we'll keep them nullable for now


def downgrade() -> None:
    # Drop foreign key constraints and columns
    op.drop_constraint(
        "fk_ingredient_names_user_id", "ingredient_names", type_="foreignkey"
    )
    op.drop_column("ingredient_names", "user_id")

    op.drop_constraint("fk_recipe_names_user_id", "recipe_names", type_="foreignkey")
    op.drop_column("recipe_names", "user_id")

    op.drop_column("users", "is_admin")
