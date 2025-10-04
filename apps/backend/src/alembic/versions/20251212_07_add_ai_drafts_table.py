"""Add AI drafts table for temporary recipe suggestions

Revision ID: 20251212_07
Revises: 20250907_06
Create Date: 2025-12-12

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision = "20251212_07"
down_revision = "20250907_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ai_drafts table for temporary AI-generated content storage."""
    op.create_table(
        "ai_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="User who owns this draft",
        ),
        sa.Column(
            "type",
            sa.String(length=50),
            nullable=False,
            comment="Type of draft: recipe_suggestion, mealplan_suggestion, etc.",
        ),
        sa.Column(
            "payload",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            comment="JSON payload containing the AI-generated content",
        ),
        sa.Column(
            "source_url",
            sa.Text(),
            nullable=True,
            comment="Original URL if extracted from web content",
        ),
        sa.Column(
            "prompt_used",
            sa.Text(),
            nullable=True,
            comment="The prompt used for AI generation",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this draft expires and should be deleted",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_ai_drafts_user_id", ondelete="CASCADE"
        ),
    )

    # Add indexes for performance
    op.create_index("ix_ai_drafts_user_id", "ai_drafts", ["user_id"])
    op.create_index("ix_ai_drafts_expires_at", "ai_drafts", ["expires_at"])
    op.create_index("ix_ai_drafts_type", "ai_drafts", ["type"])


def downgrade() -> None:
    """Drop ai_drafts table."""
    op.drop_index("ix_ai_drafts_type", table_name="ai_drafts")
    op.drop_index("ix_ai_drafts_expires_at", table_name="ai_drafts")
    op.drop_index("ix_ai_drafts_user_id", table_name="ai_drafts")
    op.drop_table("ai_drafts")
