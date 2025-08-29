"""add difficulty column to recipe_names

Revision ID: 20250827_03
Revises: 20250827_02
Create Date: 2025-08-27

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "20250827_03"
down_revision = "20250827_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recipe_names",
        sa.Column("difficulty", sa.String(length=50), nullable=True),
    )

    # Optional: set a default difficulty to 'medium' where NULL
    op.execute("UPDATE recipe_names SET difficulty = 'medium' WHERE difficulty IS NULL")


def downgrade() -> None:
    op.drop_column("recipe_names", "difficulty")
