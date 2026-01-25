"""Tests for user preferences location fields and geocoding integration."""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from models.user_preferences import UserPreferences
from schemas.user_preferences import UserPreferencesUpdate


@pytest_asyncio.fixture
async def preferences_db_session() -> AsyncSession:
    """SQLite session with a minimal user_preferences table including CHECK constraints.

    We cannot create the full SQLAlchemy model schema in SQLite because the
    production model includes Postgres-specific types (e.g., ARRAY). This fixture
    creates a SQLite-compatible subset that includes the latitude/longitude CHECK
    constraints we rely on at the DB level.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            """
            CREATE TABLE user_preferences (
                id BLOB PRIMARY KEY,
                user_id BLOB NOT NULL UNIQUE,
                family_size INTEGER NOT NULL DEFAULT 2,
                latitude NUMERIC,
                longitude NUMERIC,
                CONSTRAINT ck_user_preferences_latitude_valid
                    CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90)),
                CONSTRAINT ck_user_preferences_longitude_valid
                    CHECK (
                        longitude IS NULL
                        OR (longitude >= -180 AND longitude <= 180)
                    )
            )
            """
        )

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_preferences_schema_validates_country_code() -> None:
    """Test that country code is validated and uppercased."""
    # Lowercase should be uppercased
    update = UserPreferencesUpdate(country="us")
    assert update.country == "US"

    update2 = UserPreferencesUpdate(country="gb")
    assert update2.country == "GB"


@pytest.mark.asyncio
async def test_preferences_location_fields_nullable() -> None:
    """Test that location fields are nullable in the model."""
    prefs = UserPreferences(
        user_id=uuid4(),
        family_size=2,
        # All location fields should default to None
    )

    assert prefs.city is None
    assert prefs.state_or_region is None
    assert prefs.postal_code is None
    # country has server default 'US' but may be None in model without DB insert
    assert prefs.latitude is None
    assert prefs.longitude is None
    assert prefs.timezone is None
    assert prefs.geocoded_at is None


@pytest.mark.asyncio
async def test_preferences_latitude_longitude_constraints() -> None:
    """Test latitude and longitude value constraints."""
    prefs = UserPreferences(
        user_id=uuid4(),
        family_size=2,
    )

    # Valid latitude/longitude
    prefs.latitude = 45.0
    prefs.longitude = -122.0
    assert prefs.latitude == 45.0
    assert prefs.longitude == -122.0

    # Edge cases
    prefs.latitude = 90.0  # North pole
    prefs.longitude = 180.0  # Date line
    assert prefs.latitude == 90.0
    assert prefs.longitude == 180.0

    prefs.latitude = -90.0  # South pole
    prefs.longitude = -180.0  # Date line
    assert prefs.latitude == -90.0
    assert prefs.longitude == -180.0


@pytest.mark.asyncio
async def test_preferences_latitude_longitude_constraints_enforced_in_db(
    preferences_db_session: AsyncSession,
) -> None:
    """Verify DB-level CHECK constraints reject invalid lat/lon values."""
    # Valid insert should succeed
    await preferences_db_session.execute(
        text(
            """
            INSERT INTO user_preferences (
                id,
                user_id,
                family_size,
                latitude,
                longitude
            )
            VALUES (:id, :user_id, :family_size, :latitude, :longitude)
            """
        ),
        {
            "id": uuid4().bytes,
            "user_id": uuid4().bytes,
            "family_size": 2,
            "latitude": 45.0,
            "longitude": -122.0,
        },
    )
    await preferences_db_session.commit()

    # Invalid latitude should fail
    with pytest.raises(IntegrityError):
        await preferences_db_session.execute(
            text(
                """
                INSERT INTO user_preferences (
                    id,
                    user_id,
                    family_size,
                    latitude,
                    longitude
                )
                VALUES (:id, :user_id, :family_size, :latitude, :longitude)
                """
            ),
            {
                "id": uuid4().bytes,
                "user_id": uuid4().bytes,
                "family_size": 2,
                "latitude": 91.0,
                "longitude": 0.0,
            },
        )
        await preferences_db_session.commit()

    await preferences_db_session.rollback()

    # Invalid longitude should fail
    with pytest.raises(IntegrityError):
        await preferences_db_session.execute(
            text(
                """
                INSERT INTO user_preferences (
                    id,
                    user_id,
                    family_size,
                    latitude,
                    longitude
                )
                VALUES (:id, :user_id, :family_size, :latitude, :longitude)
                """
            ),
            {
                "id": uuid4().bytes,
                "user_id": uuid4().bytes,
                "family_size": 2,
                "latitude": 0.0,
                "longitude": 181.0,
            },
        )
        await preferences_db_session.commit()
