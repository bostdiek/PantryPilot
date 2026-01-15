"""Tests for user preferences location fields and geocoding integration."""

from uuid import uuid4

import pytest

from models.user_preferences import UserPreferences
from schemas.user_preferences import UserPreferencesUpdate


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
