"""initial schema

Revision ID: 20250827_00
Revises:
Create Date: 2025-08-27

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "20250827_00"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "username",
                sa.String(length=255),
                nullable=False,
                unique=True,
            ),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("first_name", sa.String(length=255), nullable=True),
            sa.Column("last_name", sa.String(length=255), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
        )

    if not insp.has_table("ingredient_names"):
        op.create_table(
            "ingredient_names",
            sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
            sa.Column("ingredient_name", sa.String(length=255), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
        )

    if not insp.has_table("recipe_names"):
        op.create_table(
            "recipe_names",
            sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("prep_time_minutes", sa.Integer(), nullable=True),
            sa.Column("cook_time_minutes", sa.Integer(), nullable=True),
            sa.Column("total_time_minutes", sa.Integer(), nullable=True),
            sa.Column("serving_min", sa.Integer(), nullable=True),
            sa.Column("serving_max", sa.Integer(), nullable=True),
            sa.Column("ethnicity", sa.String(length=255), nullable=True),
            sa.Column("course_type", sa.String(length=255), nullable=True),
            sa.Column("instructions", sa.ARRAY(sa.Text()), nullable=True),
            sa.Column("user_notes", sa.Text(), nullable=True),
            sa.Column("ai_summary", sa.Text(), nullable=True),
            sa.Column("link_source", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
        )

    if not insp.has_table("recipe_ingredients"):
        op.create_table(
            "recipe_ingredients",
            sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "recipe_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("recipe_names.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "ingredient_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("ingredient_names.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("quantity_value", sa.Numeric(), nullable=True),
            sa.Column("quantity_unit", sa.String(length=64), nullable=True),
            sa.Column(
                "prep",
                sa.JSON(),
                server_default=sa.text("'{}'::jsonb"),
                nullable=True,
            ),
            sa.Column(
                "is_optional",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=True,
            ),
            sa.Column("user_notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
        )

    if not insp.has_table("meal_history"):
        op.create_table(
            "meal_history",
            sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "recipe_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("recipe_names.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("date_suggested", sa.DateTime(timezone=True), nullable=True),
            sa.Column("week_suggested", sa.Integer(), nullable=True),
            sa.Column(
                "was_cooked",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
        )


def downgrade() -> None:
    op.drop_table("meal_history")
    op.drop_table("recipe_ingredients")
    op.drop_table("recipe_names")
    op.drop_table("ingredient_names")
    op.drop_table("users")
