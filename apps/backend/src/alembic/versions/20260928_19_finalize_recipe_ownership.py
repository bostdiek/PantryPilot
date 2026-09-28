"""Finalize recipe and ingredient ownership.

Revision ID: 20260928_19
Revises: 20260131_18
Create Date: 2026-09-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op


revision: str = "20260928_19"
down_revision: str | None = "20260131_18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_recovery_tables() -> None:
    op.create_table(
        "ownership_recipe_assignments",
        sa.Column(
            "recipe_id",
            UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("assigned_user_id", UUID(as_uuid=True), nullable=False),
    )
    op.create_table(
        "ownership_recipe_quarantine",
        sa.Column("source_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("payload", JSONB(), nullable=False),
    )
    op.create_table(
        "ownership_ingredient_quarantine",
        sa.Column("source_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("payload", JSONB(), nullable=False),
    )
    op.create_table(
        "ownership_recipe_ingredient_quarantine",
        sa.Column("source_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("payload", JSONB(), nullable=False),
    )
    op.create_table(
        "ownership_meal_link_quarantine",
        sa.Column("meal_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("recipe_id", UUID(as_uuid=True), nullable=False),
    )
    op.create_table(
        "ownership_ingredient_mappings",
        sa.Column("source_ingredient_id", UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_ingredient_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_created", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("source_ingredient_id", "owner_id"),
    )
    op.create_table(
        "ownership_recipe_ingredient_mappings",
        sa.Column(
            "recipe_ingredient_id",
            UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("source_ingredient_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_ingredient_id", UUID(as_uuid=True), nullable=False),
    )


def _assign_reliable_recipe_owners() -> None:
    op.execute("""
        INSERT INTO ownership_recipe_assignments (recipe_id, assigned_user_id)
        SELECT r.id, (ARRAY_AGG(DISTINCT m.user_id))[1]
        FROM recipe_names AS r
        JOIN meal_history AS m ON m.recipe_id = r.id
        WHERE r.user_id IS NULL
        GROUP BY r.id
        HAVING COUNT(DISTINCT m.user_id) = 1
    """)
    op.execute("""
        UPDATE recipe_names AS r
        SET user_id = a.assigned_user_id
        FROM ownership_recipe_assignments AS a
        WHERE r.id = a.recipe_id
    """)


def _quarantine_cross_user_meal_links() -> None:
    op.execute("""
        INSERT INTO ownership_meal_link_quarantine (meal_id, recipe_id)
        SELECT m.id, m.recipe_id
        FROM meal_history AS m
        JOIN recipe_names AS r ON r.id = m.recipe_id
        WHERE r.user_id IS NOT NULL
          AND m.user_id <> r.user_id
    """)
    op.execute("""
        UPDATE meal_history AS m
        SET recipe_id = NULL
        FROM ownership_meal_link_quarantine AS q
        WHERE m.id = q.meal_id
    """)


def _quarantine_unresolved_recipes() -> None:
    op.execute("""
        INSERT INTO ownership_recipe_quarantine (source_id, payload)
        SELECT r.id, to_jsonb(r)
        FROM recipe_names AS r
        WHERE r.user_id IS NULL
    """)
    op.execute("""
        INSERT INTO ownership_recipe_ingredient_quarantine (source_id, payload)
        SELECT ri.id, to_jsonb(ri)
        FROM recipe_ingredients AS ri
        JOIN ownership_recipe_quarantine AS q
          ON q.source_id = ri.recipe_id
    """)
    op.execute("""
        INSERT INTO ownership_meal_link_quarantine (meal_id, recipe_id)
        SELECT m.id, m.recipe_id
        FROM meal_history AS m
        JOIN ownership_recipe_quarantine AS q
          ON q.source_id = m.recipe_id
    """)
    op.execute("""
        UPDATE meal_history AS m
        SET recipe_id = NULL
        FROM ownership_meal_link_quarantine AS q
        WHERE m.id = q.meal_id
    """)
    op.execute("""
        DELETE FROM recipe_ingredients AS ri
        USING ownership_recipe_quarantine AS q
        WHERE ri.recipe_id = q.source_id
    """)
    op.execute("""
        DELETE FROM recipe_names AS r
        USING ownership_recipe_quarantine AS q
        WHERE r.id = q.source_id
    """)


def _migrate_legacy_ingredients() -> None:
    op.execute("""
        WITH candidates AS (
            SELECT DISTINCT
                i.id AS source_ingredient_id,
                r.user_id AS owner_id,
                LOWER(i.ingredient_name) AS normalized_name
            FROM ingredient_names AS i
            JOIN recipe_ingredients AS ri ON ri.ingredient_id = i.id
            JOIN recipe_names AS r ON r.id = ri.recipe_id
            WHERE i.user_id IS NULL
        ),
        candidate_groups AS (
            SELECT DISTINCT owner_id, normalized_name
            FROM candidates
        ),
        existing_targets AS (
            SELECT
                g.owner_id,
                g.normalized_name,
                (
                    SELECT owned.id
                    FROM ingredient_names AS owned
                    WHERE owned.user_id = g.owner_id
                      AND LOWER(owned.ingredient_name) = g.normalized_name
                    ORDER BY owned.created_at, owned.id
                    LIMIT 1
                ) AS existing_target_id
            FROM candidate_groups AS g
        ),
        resolved_targets AS MATERIALIZED (
            SELECT
                owner_id,
                normalized_name,
                COALESCE(existing_target_id, uuid_generate_v4()) AS target_id,
                existing_target_id IS NULL AS target_created
            FROM existing_targets
        )
        INSERT INTO ownership_ingredient_mappings (
            source_ingredient_id,
            owner_id,
            target_ingredient_id,
            target_created
        )
        SELECT
            c.source_ingredient_id,
            c.owner_id,
            t.target_id,
            t.target_created
        FROM candidates AS c
        JOIN resolved_targets AS t
          ON t.owner_id = c.owner_id
         AND t.normalized_name = c.normalized_name
    """)
    op.execute("""
        INSERT INTO ingredient_names (
            id,
            user_id,
            ingredient_name,
            created_at,
            updated_at
        )
        SELECT DISTINCT ON (m.target_ingredient_id)
            m.target_ingredient_id,
            m.owner_id,
            i.ingredient_name,
            i.created_at,
            i.updated_at
        FROM ownership_ingredient_mappings AS m
        JOIN ingredient_names AS i ON i.id = m.source_ingredient_id
        WHERE m.target_created
        ORDER BY m.target_ingredient_id, i.created_at, i.id
    """)
    op.execute("""
        INSERT INTO ownership_recipe_ingredient_mappings (
            recipe_ingredient_id,
            source_ingredient_id,
            target_ingredient_id
        )
        SELECT
            ri.id,
            ri.ingredient_id,
            m.target_ingredient_id
        FROM recipe_ingredients AS ri
        JOIN recipe_names AS r ON r.id = ri.recipe_id
        JOIN ownership_ingredient_mappings AS m
          ON m.source_ingredient_id = ri.ingredient_id
         AND m.owner_id = r.user_id
    """)
    op.execute("""
        UPDATE recipe_ingredients AS ri
        SET ingredient_id = m.target_ingredient_id
        FROM ownership_recipe_ingredient_mappings AS m
        WHERE ri.id = m.recipe_ingredient_id
    """)
    op.execute("""
        INSERT INTO ownership_ingredient_quarantine (source_id, payload)
        SELECT i.id, to_jsonb(i)
        FROM ingredient_names AS i
        WHERE i.user_id IS NULL
    """)
    op.execute("DELETE FROM ingredient_names WHERE user_id IS NULL")


def _verify_ownership() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM recipe_names WHERE user_id IS NULL) THEN
                RAISE EXCEPTION 'recipe ownership migration left null owners';
            END IF;
            IF EXISTS (SELECT 1 FROM ingredient_names WHERE user_id IS NULL) THEN
                RAISE EXCEPTION 'ingredient ownership migration left null owners';
            END IF;
        END
        $$;
    """)


def upgrade() -> None:
    """Assign reliable owners, quarantine unresolved data, and require ownership."""
    _create_recovery_tables()
    _assign_reliable_recipe_owners()
    _quarantine_cross_user_meal_links()
    _quarantine_unresolved_recipes()
    _migrate_legacy_ingredients()
    _verify_ownership()

    op.alter_column(
        "recipe_names",
        "user_id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "ingredient_names",
        "user_id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )


def downgrade() -> None:
    """Restore quarantined legacy data and nullable ownership."""
    op.alter_column(
        "ingredient_names",
        "user_id",
        existing_type=UUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "recipe_names",
        "user_id",
        existing_type=UUID(as_uuid=True),
        nullable=True,
    )

    op.execute("""
        INSERT INTO ingredient_names
        SELECT (jsonb_populate_record(NULL::ingredient_names, q.payload)).*
        FROM ownership_ingredient_quarantine AS q
        ON CONFLICT (id) DO NOTHING
    """)
    op.execute("""
        INSERT INTO recipe_names
        SELECT (jsonb_populate_record(NULL::recipe_names, q.payload)).*
        FROM ownership_recipe_quarantine AS q
        ON CONFLICT (id) DO NOTHING
    """)
    op.execute("""
        UPDATE recipe_ingredients AS ri
        SET ingredient_id = m.source_ingredient_id
        FROM ownership_recipe_ingredient_mappings AS m
        WHERE ri.id = m.recipe_ingredient_id
          AND ri.ingredient_id = m.target_ingredient_id
    """)
    op.execute("""
        INSERT INTO recipe_ingredients
        SELECT (
            jsonb_populate_record(NULL::recipe_ingredients, q.payload)
        ).*
        FROM ownership_recipe_ingredient_quarantine AS q
        ON CONFLICT (id) DO NOTHING
    """)
    op.execute("""
        UPDATE meal_history AS m
        SET recipe_id = q.recipe_id
        FROM ownership_meal_link_quarantine AS q
        WHERE m.id = q.meal_id
    """)
    op.execute("""
        UPDATE recipe_names AS r
        SET user_id = NULL
        FROM ownership_recipe_assignments AS a
        WHERE r.id = a.recipe_id
    """)
    op.execute("""
        DELETE FROM ingredient_names AS i
        USING ownership_ingredient_mappings AS m
        WHERE i.id = m.target_ingredient_id
          AND m.target_created
          AND NOT EXISTS (
              SELECT 1
              FROM recipe_ingredients AS ri
              WHERE ri.ingredient_id = i.id
          )
    """)

    op.drop_table("ownership_recipe_ingredient_mappings")
    op.drop_table("ownership_ingredient_mappings")
    op.drop_table("ownership_meal_link_quarantine")
    op.drop_table("ownership_recipe_ingredient_quarantine")
    op.drop_table("ownership_ingredient_quarantine")
    op.drop_table("ownership_recipe_quarantine")
    op.drop_table("ownership_recipe_assignments")
