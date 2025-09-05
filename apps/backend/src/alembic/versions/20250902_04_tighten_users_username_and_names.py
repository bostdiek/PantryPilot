"""tighten users: username/name lengths and username check

Revision ID: 20250902_04
Revises: 20250827_03
Create Date: 2025-09-02

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "20250902_04"
down_revision = "20250827_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Note: shrinking lengths can fail if existing data exceeds new limits.
    op.alter_column(
        "users",
        "username",
        type_=sa.String(length=50),
        existing_type=sa.String(length=255),
        existing_nullable=False,
        existing_server_default=None,
    )
    op.alter_column(
        "users",
        "first_name",
        type_=sa.String(length=50),
        existing_type=sa.String(length=255),
        existing_nullable=True,
        existing_server_default=None,
    )
    op.alter_column(
        "users",
        "last_name",
        type_=sa.String(length=50),
        existing_type=sa.String(length=255),
        existing_nullable=True,
        existing_server_default=None,
    )

    # Enforce username length at DB level (3–50)
    op.create_check_constraint(
        "ck_users_username_len",
        "users",
        "length(username) BETWEEN 3 AND 50",
    )


def downgrade() -> None:
    # Drop the username length check
    op.drop_constraint("ck_users_username_len", "users", type_="check")

    # Revert lengths
    op.alter_column(
        "users",
        "last_name",
        type_=sa.String(length=255),
        existing_type=sa.String(length=50),
        existing_nullable=True,
        existing_server_default=None,
    )
    op.alter_column(
        "users",
        "first_name",
        type_=sa.String(length=255),
        existing_type=sa.String(length=50),
        existing_nullable=True,
        existing_server_default=None,
    )
    op.alter_column(
        "users",
        "username",
        type_=sa.String(length=255),
        existing_type=sa.String(length=50),
        existing_nullable=False,
        existing_server_default=None,
    )
