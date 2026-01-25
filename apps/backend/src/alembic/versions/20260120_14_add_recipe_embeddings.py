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
    # Note: In Azure PostgreSQL, the extension must be enabled via
    # infrastructure (azure.extensions configuration parameter).
    # This command will work locally and in environments where extensions
    # can be created via SQL.
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except sa.exc.DBAPIError as e:
        # Only ignore the specific Azure extension allow-list error
        if 'extension "vector" is not allow-listed' in str(e):
            # Azure PostgreSQL: extension must be enabled via azure.extensions config
            pass
        else:
            # Re-raise any other database errors (permissions, connection, etc.)
            raise

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

    # ⚠️ DESTRUCTIVE OPERATION: Clean up duplicate recipe names
    # This keeps the OLDEST recipe for each (user_id, LOWER(name)) combination.
    # Duplicates (newer entries with same name) will be DELETED.
    #
    # IMPORTANT: Ensure you have a database backup before running this migration!
    # Run: make db-backup  (or see db/backup.sh for manual backup)
    #
    # To preview affected records before migration:
    #   SELECT id, user_id, name, created_at FROM recipe_names
    #   WHERE id IN (
    #     SELECT id FROM (
    #       SELECT id, ROW_NUMBER() OVER (
    #         PARTITION BY user_id, LOWER(name) ORDER BY created_at ASC
    #       ) as rn FROM recipe_names
    #     ) t WHERE rn > 1
    #   );
    op.execute("""
        DELETE FROM recipe_names
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY user_id, LOWER(name)
                           ORDER BY created_at ASC
                       ) as rn
                FROM recipe_names
            ) t
            WHERE rn > 1
        )
    """)

    # ⚠️ DESTRUCTIVE OPERATION: Clean up duplicate ingredient names
    # This keeps the OLDEST ingredient for each (user_id, LOWER(ingredient_name))
    # combination. Duplicates (newer entries with same name) will be DELETED.
    # See backup instructions above.
    op.execute("""
        DELETE FROM ingredient_names
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY user_id, LOWER(ingredient_name)
                           ORDER BY created_at ASC
                       ) as rn
                FROM ingredient_names
            ) t
            WHERE rn > 1
        )
    """)

    # Add deduplication indexes to prevent duplicate recipes per user
    # Note: ingredient_names already has a UniqueConstraint at the model level,
    # but we add a functional index here for case-insensitive uniqueness
    op.execute("""
        CREATE UNIQUE INDEX idx_recipe_names_user_name_unique
        ON recipe_names (user_id, LOWER(name))
    """)

    # Add deduplication index for ingredients as well
    # This supplements the existing uq_ingredient_user_name constraint
    # with case-insensitive matching
    op.execute("""
        CREATE UNIQUE INDEX idx_ingredient_names_user_name_unique
        ON ingredient_names (user_id, LOWER(ingredient_name))
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
