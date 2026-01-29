"""Add title_updated_at column to chat_conversations

This column tracks when a conversation title was AI-generated.
NULL means the title has never been generated (needs title generation).
A timestamp means the title was AI-generated at that time.

Revision ID: 20260129_16
Revises: 20260123_15
Create Date: 2026-01-29

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260129_16"
down_revision = "20260123_15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add title_updated_at column to chat_conversations table."""
    op.add_column(
        "chat_conversations",
        sa.Column(
            "title_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the title was last AI-generated (NULL = needs title)",
        ),
    )


def downgrade() -> None:
    """Remove title_updated_at column from chat_conversations table."""
    op.drop_column("chat_conversations", "title_updated_at")
