"""extend meal_history for planning

Revision ID: 20250827_01
Revises:
Create Date: 2025-08-27

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "20250827_01"
down_revision = "20250827_00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to meal_history
    op.add_column(
        "meal_history",
        sa.Column("planned_for_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "meal_history",
        sa.Column("meal_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "meal_history",
        sa.Column("order_index", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "meal_history",
        sa.Column(
            "is_leftover",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "meal_history",
        sa.Column(
            "is_eating_out",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "meal_history",
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "meal_history",
        sa.Column("cooked_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create helpful indexes
    op.create_index(
        "ix_meal_history_user_planned_date",
        "meal_history",
        ["user_id", "planned_for_date"],
    )
    op.create_index(
        "ix_meal_history_user_recipe_cooked",
        "meal_history",
        ["user_id", "recipe_id", "was_cooked"],
    )


def downgrade() -> None:
    op.drop_index("ix_meal_history_user_recipe_cooked", table_name="meal_history")
    op.drop_index("ix_meal_history_user_planned_date", table_name="meal_history")
    op.drop_column("meal_history", "cooked_at")
    op.drop_column("meal_history", "notes")
    op.drop_column("meal_history", "is_eating_out")
    op.drop_column("meal_history", "is_leftover")
    op.drop_column("meal_history", "order_index")
    op.drop_column("meal_history", "meal_type")
    op.drop_column("meal_history", "planned_for_date")
