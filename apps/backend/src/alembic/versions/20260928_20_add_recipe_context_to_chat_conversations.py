"""Add recipe context to chat conversations.

Revision ID: 20260928_20
Revises: 20260928_19
Create Date: 2026-09-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op


revision: str = "20260928_20"
down_revision: str | None = "20260928_19"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_conversations",
        sa.Column("recipe_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "chat_conversations",
        sa.Column(
            "is_current_for_recipe",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_chat_conversations_recipe_id_recipe_names",
        "chat_conversations",
        "recipe_names",
        ["recipe_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_chat_conversations_recipe_id",
        "chat_conversations",
        ["recipe_id"],
    )
    op.create_index(
        "ix_chat_conversations_user_recipe",
        "chat_conversations",
        ["user_id", "recipe_id"],
    )
    op.create_index(
        "uq_chat_conversations_current_recipe",
        "chat_conversations",
        ["user_id", "recipe_id"],
        unique=True,
        postgresql_where=sa.text("recipe_id IS NOT NULL AND is_current_for_recipe"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_chat_conversations_current_recipe",
        table_name="chat_conversations",
    )
    op.drop_index(
        "ix_chat_conversations_user_recipe",
        table_name="chat_conversations",
    )
    op.drop_index(
        "ix_chat_conversations_recipe_id",
        table_name="chat_conversations",
    )
    op.drop_constraint(
        "fk_chat_conversations_recipe_id_recipe_names",
        "chat_conversations",
        type_="foreignkey",
    )
    op.drop_column("chat_conversations", "is_current_for_recipe")
    op.drop_column("chat_conversations", "recipe_id")
