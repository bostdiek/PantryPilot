"""Add chat conversations and messages tables

Revision ID: 20260115_10
Revises: 20260109_09
Create Date: 2026-01-15

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260115_10"
down_revision = "20260109_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create chat_conversations and chat_messages tables."""

    op.create_table(
        "chat_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="User who owns this conversation",
        ),
        sa.Column(
            "title",
            sa.Text(),
            nullable=True,
            comment="Optional user-visible conversation title",
        ),
        sa.Column(
            "summary",
            sa.Text(),
            nullable=True,
            comment="Durable summary of the conversation",
        ),
        sa.Column(
            "summary_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the summary was last updated",
        ),
        sa.Column(
            "summary_message_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Message id the summary was derived from (best-effort)",
        ),
        sa.Column(
            "summary_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Summary provenance/strategy metadata",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Last time a message/tool event occurred in the conversation",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_chat_conversations_user_id",
            ondelete="CASCADE",
        ),
    )

    op.create_index("ix_chat_conversations_user_id", "chat_conversations", ["user_id"])
    op.create_index(
        "ix_chat_conversations_last_activity_at",
        "chat_conversations",
        ["last_activity_at"],
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            comment="Message role: user|assistant|system|tool",
        ),
        sa.Column(
            "content_blocks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="Canonical multimodal content blocks",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Non-LLM metadata (provenance, routing hints, etc)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chat_conversations.id"],
            name="fk_chat_messages_conversation_id_chat_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_chat_messages_user_id_users",
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"]
    )
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])

    op.create_foreign_key(
        "fk_chat_conversations_summary_message_id_chat_messages",
        "chat_conversations",
        "chat_messages",
        ["summary_message_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Drop chat_conversations and chat_messages tables."""

    op.drop_constraint(
        "fk_chat_conversations_summary_message_id_chat_messages",
        "chat_conversations",
        type_="foreignkey",
    )

    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_conversation_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index(
        "ix_chat_conversations_last_activity_at", table_name="chat_conversations"
    )
    op.drop_index("ix_chat_conversations_user_id", table_name="chat_conversations")
    op.drop_table("chat_conversations")
