"""Add ai_training_samples table

Stores raw LLM interactions for fine-tuning with 1-year retention.

Revision ID: 20260130_17
Revises: 20260129_16
Create Date: 2026-01-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260130_17"
down_revision: str | None = "20260129_16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create ai_training_samples table for LLM training data capture."""
    op.create_table(
        "ai_training_samples",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "raw_prompt",
            sa.Text(),
            nullable=False,
            comment="Full prompt sent to LLM including system messages and context",
        ),
        sa.Column(
            "raw_response",
            sa.Text(),
            nullable=False,
            comment="Raw LLM output before parsing",
        ),
        sa.Column(
            "tool_calls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="List of tool calls in this turn for training format",
        ),
        sa.Column(
            "model_name",
            sa.String(length=100),
            nullable=False,
            comment="LLM model identifier",
        ),
        sa.Column(
            "model_version",
            sa.String(length=50),
            nullable=True,
            comment="Model version if available",
        ),
        sa.Column(
            "temperature",
            sa.Float(),
            nullable=True,
            comment="Temperature parameter used",
        ),
        sa.Column(
            "max_tokens",
            sa.Integer(),
            nullable=True,
            comment="Max tokens parameter used",
        ),
        sa.Column(
            "prompt_tokens",
            sa.Integer(),
            nullable=True,
            comment="Token count for input",
        ),
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=True,
            comment="Token count for output",
        ),
        sa.Column(
            "latency_ms",
            sa.Integer(),
            nullable=True,
            comment="Total response time in milliseconds",
        ),
        sa.Column(
            "user_feedback",
            sa.String(length=20),
            nullable=True,
            comment="User rating: positive|negative",
        ),
        sa.Column(
            "is_simulated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="True if from synthetic data generation, False if real user",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chat_conversations.id"],
            name=op.f("fk_ai_training_samples_conversation_id_chat_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            name=op.f("fk_ai_training_samples_message_id_chat_messages"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_ai_training_samples_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_training_samples")),
    )

    # Create indexes for query performance
    op.create_index(
        "ix_training_samples_created_at",
        "ai_training_samples",
        ["created_at"],
    )
    op.create_index(
        "ix_training_samples_conversation_id",
        "ai_training_samples",
        ["conversation_id"],
    )
    op.create_index(
        "ix_training_samples_feedback",
        "ai_training_samples",
        ["user_feedback"],
    )


def downgrade() -> None:
    """Drop ai_training_samples table."""
    op.drop_index("ix_training_samples_feedback", table_name="ai_training_samples")
    op.drop_index(
        "ix_training_samples_conversation_id", table_name="ai_training_samples"
    )
    op.drop_index("ix_training_samples_created_at", table_name="ai_training_samples")
    op.drop_table("ai_training_samples")
