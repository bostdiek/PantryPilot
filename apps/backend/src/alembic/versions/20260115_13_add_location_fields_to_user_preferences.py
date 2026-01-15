"""Add location fields to user_preferences

Revision ID: 20260115_13
Revises: 20260115_12
Create Date: 2026-01-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260115_13"
down_revision: str | None = "20260115_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add location fields to user_preferences table."""
    # Add user-facing location fields
    op.add_column(
        "user_preferences",
        sa.Column(
            "city",
            sa.String(length=100),
            nullable=True,
            comment="User's city (for weather and meal planning)",
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "state_or_region",
            sa.String(length=100),
            nullable=True,
            comment="State/region/province (e.g., 'CA', 'Ontario')",
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "postal_code",
            sa.String(length=20),
            nullable=True,
            comment="Postal/ZIP code",
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "country",
            sa.String(length=2),
            nullable=True,
            server_default=sa.text("'US'"),
            comment="ISO 3166-1 alpha-2 country code (default US)",
        ),
    )

    # Add internal geocoded fields
    op.add_column(
        "user_preferences",
        sa.Column(
            "latitude",
            sa.Numeric(precision=9, scale=6),
            nullable=True,
            comment="Geocoded latitude (-90 to 90)",
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "longitude",
            sa.Numeric(precision=9, scale=6),
            nullable=True,
            comment="Geocoded longitude (-180 to 180)",
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "timezone",
            sa.String(length=50),
            nullable=True,
            comment="IANA timezone identifier (e.g., 'America/New_York')",
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "geocoded_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last geocoding timestamp",
        ),
    )

    # Add check constraints for latitude and longitude
    op.create_check_constraint(
        "ck_user_preferences_latitude_valid",
        "user_preferences",
        "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
    )
    op.create_check_constraint(
        "ck_user_preferences_longitude_valid",
        "user_preferences",
        "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
    )


def downgrade() -> None:
    """Remove location fields from user_preferences table."""
    # Drop check constraints
    op.drop_constraint(
        "ck_user_preferences_latitude_valid", "user_preferences", type_="check"
    )
    op.drop_constraint(
        "ck_user_preferences_longitude_valid", "user_preferences", type_="check"
    )

    # Drop columns
    op.drop_column("user_preferences", "geocoded_at")
    op.drop_column("user_preferences", "timezone")
    op.drop_column("user_preferences", "longitude")
    op.drop_column("user_preferences", "latitude")
    op.drop_column("user_preferences", "country")
    op.drop_column("user_preferences", "postal_code")
    op.drop_column("user_preferences", "state_or_region")
    op.drop_column("user_preferences", "city")
