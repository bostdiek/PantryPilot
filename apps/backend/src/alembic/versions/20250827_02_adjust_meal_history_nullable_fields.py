"""adjust meal_history nullable fields for planning and non-recipe entries

Revision ID: 20250827_02
Revises: 20250827_01
Create Date: 2025-08-27

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "20250827_02"
down_revision = "20250827_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Allow non-recipe entries: recipe_id becomes nullable
    op.alter_column(
        "meal_history",
        "recipe_id",
        existing_type=sa.UUID(),
        nullable=True,
        existing_nullable=False,
    )

    # Planning fields should be non-null with defaults
    op.alter_column(
        "meal_history",
        "planned_for_date",
        existing_type=sa.Date(),
        nullable=False,
        existing_nullable=True,
    )
    op.alter_column(
        "meal_history",
        "meal_type",
        existing_type=sa.String(length=50),
        nullable=False,
        existing_nullable=True,
        server_default="dinner",
    )
    op.alter_column(
        "meal_history",
        "order_index",
        existing_type=sa.Integer(),
        nullable=False,
        existing_nullable=True,
        server_default="0",
    )


def downgrade() -> None:
    op.alter_column(
        "meal_history",
        "order_index",
        existing_type=sa.Integer(),
        nullable=True,
        existing_nullable=False,
        server_default=None,
    )
    op.alter_column(
        "meal_history",
        "meal_type",
        existing_type=sa.String(length=50),
        nullable=True,
        existing_nullable=False,
        server_default=None,
    )
    op.alter_column(
        "meal_history",
        "planned_for_date",
        existing_type=sa.Date(),
        nullable=True,
        existing_nullable=False,
    )
    op.alter_column(
        "meal_history",
        "recipe_id",
        existing_type=sa.UUID(),
        nullable=False,
        existing_nullable=True,
    )
