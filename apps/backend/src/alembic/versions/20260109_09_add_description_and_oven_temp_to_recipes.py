"""Add description and oven_temperature_f columns to recipe_names table

Revision ID: 20260109_09
Revises: 20251130_08
Create Date: 2026-01-09

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260109_09"
down_revision = "20251130_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add description and oven_temperature_f columns to recipe_names table."""
    op.add_column(
        "recipe_names",
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Recipe description",
        ),
    )
    op.add_column(
        "recipe_names",
        sa.Column(
            "oven_temperature_f",
            sa.Integer(),
            nullable=True,
            comment=(
                "Oven temperature in Fahrenheit (0-550 range enforced at app layer)"
            ),
        ),
    )


def downgrade() -> None:
    """Remove description and oven_temperature_f columns from recipe_names table."""
    op.drop_column("recipe_names", "oven_temperature_f")
    op.drop_column("recipe_names", "description")
