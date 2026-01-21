"""Add embedding and context columns to recipes for semantic search

Revision ID: 20260120_14
Revises: 20260115_13
Create Date: 2026-01-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260120_14"
down_revision: str | None = "20260115_13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add embedding and context columns, plus deduplication indexes."""
    # Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add embedding column (768 dimensions for Gemini)
    op.add_column(
        "recipe_names",
        sa.Column("embedding", Vector(768), nullable=True),
    )

    # Add context columns for transparency/debugging
    op.add_column(
        "recipe_names",
        sa.Column("search_context", sa.Text(), nullable=True),
    )
    op.add_column(
        "recipe_names",
        sa.Column(
            "search_context_generated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # HNSW index for vector similarity (m=16, ef_construction=64 are good defaults)
    op.execute("""
        CREATE INDEX idx_recipe_names_embedding
        ON recipe_names
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # Add deduplication indexes to prevent duplicate recipes per user
    # Partial unique index: prevent same user from creating duplicate recipe names
    op.execute("""
        CREATE UNIQUE INDEX idx_recipe_names_user_name_unique
        ON recipe_names (user_id, LOWER(name))
        WHERE deleted_at IS NULL
    """)

    # Add deduplication index for ingredients as well
    op.execute("""
        CREATE UNIQUE INDEX idx_ingredient_names_user_name_unique
        ON ingredient_names (user_id, LOWER(name))
        WHERE deleted_at IS NULL
    """)


def downgrade() -> None:
    """Remove embedding, context columns, and deduplication indexes."""
    # Drop deduplication indexes
    op.drop_index(
        "idx_ingredient_names_user_name_unique", table_name="ingredient_names"
    )
    op.drop_index("idx_recipe_names_user_name_unique", table_name="recipe_names")

    # Drop embedding index
    op.drop_index("idx_recipe_names_embedding", table_name="recipe_names")

    # Drop columns
    op.drop_column("recipe_names", "search_context_generated_at")
    op.drop_column("recipe_names", "search_context")
    op.drop_column("recipe_names", "embedding")
