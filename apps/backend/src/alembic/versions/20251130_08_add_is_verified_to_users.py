"""Add is_verified column to users table

Revision ID: 20251130_08
Revises: 20251212_07
Create Date: 2025-11-30

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "20251130_08"
down_revision = "20251212_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_verified column to users table for email verification."""
    op.add_column(
        "users",
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="Whether the user has verified their email address",
        ),
    )


def downgrade() -> None:
    """Remove is_verified column from users table."""
    op.drop_column("users", "is_verified")
