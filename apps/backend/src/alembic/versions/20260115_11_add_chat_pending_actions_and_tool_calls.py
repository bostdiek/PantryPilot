"""Add chat pending actions and tool call history tables

Revision ID: 20260115_11
Revises: 20260115_10
Create Date: 2026-01-15

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260115_11"
down_revision = "20260115_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create chat_pending_actions and chat_tool_calls tables."""

    op.create_table(
        "chat_pending_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "tool_name",
            sa.String(length=100),
            nullable=False,
            comment="Tool/action identifier (app-defined)",
        ),
        sa.Column(
            "arguments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Tool call arguments (JSON-serializable)",
        ),
        sa.Column(
            "title",
            sa.Text(),
            nullable=False,
            comment="Short user-visible title describing the proposed action",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
            comment="User-visible description of what will happen",
        ),
        sa.Column(
            "confirm_label",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'Apply'"),
            comment="UI label for the accept button",
        ),
        sa.Column(
            "cancel_label",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'Cancel'"),
            comment="UI label for the cancel button",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'proposed'"),
            comment="proposed|accepted|canceled|succeeded|failed",
        ),
        sa.Column(
            "cancel_reason",
            sa.Text(),
            nullable=True,
            comment="Optional user-provided cancellation reason",
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Tool result payload (when succeeded)",
        ),
        sa.Column(
            "error",
            sa.Text(),
            nullable=True,
            comment="Error message if execution failed",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Non-LLM metadata for UI/provenance",
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
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the user accepted the proposal",
        ),
        sa.Column(
            "canceled_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the user canceled the proposal",
        ),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the tool execution completed (success or failure)",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chat_conversations.id"],
            name="fk_chat_pending_actions_conversation_id_chat_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_chat_pending_actions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            name="fk_chat_pending_actions_message_id_chat_messages",
            ondelete="SET NULL",
        ),
    )

    op.create_index(
        "ix_chat_pending_actions_conversation_id",
        "chat_pending_actions",
        ["conversation_id"],
    )
    op.create_index(
        "ix_chat_pending_actions_user_id",
        "chat_pending_actions",
        ["user_id"],
    )
    op.create_index(
        "ix_chat_pending_actions_message_id",
        "chat_pending_actions",
        ["message_id"],
    )
    op.create_index(
        "ix_chat_pending_actions_status",
        "chat_pending_actions",
        ["status"],
    )

    op.create_table(
        "chat_tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column(
            "arguments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'success'"),
            comment="success|error",
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chat_conversations.id"],
            name="fk_chat_tool_calls_conversation_id_chat_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            name="fk_chat_tool_calls_message_id_chat_messages",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_chat_tool_calls_user_id_users",
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_chat_tool_calls_conversation_id",
        "chat_tool_calls",
        ["conversation_id"],
    )
    op.create_index("ix_chat_tool_calls_message_id", "chat_tool_calls", ["message_id"])
    op.create_index("ix_chat_tool_calls_user_id", "chat_tool_calls", ["user_id"])
    op.create_index("ix_chat_tool_calls_started_at", "chat_tool_calls", ["started_at"])


def downgrade() -> None:
    """Drop chat_pending_actions and chat_tool_calls tables."""

    op.drop_index("ix_chat_tool_calls_started_at", table_name="chat_tool_calls")
    op.drop_index("ix_chat_tool_calls_user_id", table_name="chat_tool_calls")
    op.drop_index("ix_chat_tool_calls_message_id", table_name="chat_tool_calls")
    op.drop_index("ix_chat_tool_calls_conversation_id", table_name="chat_tool_calls")
    op.drop_table("chat_tool_calls")

    op.drop_index("ix_chat_pending_actions_status", table_name="chat_pending_actions")
    op.drop_index(
        "ix_chat_pending_actions_message_id",
        table_name="chat_pending_actions",
    )
    op.drop_index("ix_chat_pending_actions_user_id", table_name="chat_pending_actions")
    op.drop_index(
        "ix_chat_pending_actions_conversation_id",
        table_name="chat_pending_actions",
    )
    op.drop_table("chat_pending_actions")
