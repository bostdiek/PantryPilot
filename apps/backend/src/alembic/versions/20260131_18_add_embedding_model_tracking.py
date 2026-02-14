"""Add embedding model tracking columns to recipe_names

Revision ID: 20260131_18
Revises: 20260130_17
Create Date: 2026-01-31

This migration adds columns to track which embedding model was used to generate
each recipe's embedding vector. This enables:
1. Detection of outdated embeddings when the model changes
2. Targeted re-embedding of recipes using old models
3. Audit trail for embedding provenance
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260131_18"
down_revision: str | None = "20260130_17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add embedding model tracking columns."""
    # Track which model was used to generate the embedding
    op.add_column(
        "recipe_names",
        sa.Column(
            "embedding_model",
            sa.String(100),
            nullable=True,
            comment="Name of the model used to generate the embedding vector",
        ),
    )

    # Track when the embedding was generated (separate from context generation)
    op.add_column(
        "recipe_names",
        sa.Column(
            "embedding_generated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when the embedding vector was generated",
        ),
    )

    # Add index for efficient queries on outdated embeddings
    op.create_index(
        "idx_recipe_names_embedding_model",
        "recipe_names",
        ["embedding_model"],
        postgresql_where=sa.text("embedding IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove embedding model tracking columns."""
    op.drop_index("idx_recipe_names_embedding_model", table_name="recipe_names")
    op.drop_column("recipe_names", "embedding_generated_at")
    op.drop_column("recipe_names", "embedding_model")
