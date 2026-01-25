"""Add user_memory_documents table

Revision ID: 20260115_12
Revises: 20260115_11
Create Date: 2026-01-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260115_12"
down_revision: str | None = "20260115_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user_memory_documents table."""
    op.create_table(
        "user_memory_documents",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="User ID (FK to users table)",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
            comment="Markdown-formatted memory content",
        ),
        sa.Column(
            "format",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'markdown'"),
            comment="Content format (currently only 'markdown' supported)",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
            comment="Version counter incremented on each update",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Last update timestamp",
        ),
        sa.Column(
            "updated_by",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'assistant'"),
            comment="Who made the last update: 'assistant' or 'user'",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Additional metadata (e.g., update triggers, source messages)",
        ),
        sa.CheckConstraint(
            "format IN ('markdown')",
            name="ck_user_memory_documents_format_valid",
        ),
        sa.CheckConstraint(
            "updated_by IN ('assistant', 'user')",
            name="ck_user_memory_documents_updated_by_valid",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_user_memory_documents_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_memory_documents_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id",
            name=op.f("pk_user_memory_documents"),
        ),
    )


def downgrade() -> None:
    """Drop user_memory_documents table."""
    op.drop_table("user_memory_documents")
