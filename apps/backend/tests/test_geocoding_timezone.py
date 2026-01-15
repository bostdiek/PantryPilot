"""Tests for timezone resolution in geocoding service."""

from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.geocoding import GeocodingService


class _DummySession:
    pass


@pytest.mark.asyncio
async def test_timezone_resolution_uses_lat_lon() -> None:
    """Timezone should be resolved from coordinates when available."""
    service = GeocodingService(cast(AsyncSession, _DummySession()))

    # NYC
    assert service._get_timezone_for_lat_lon(40.7128, -74.0060) == "America/New_York"

    # Los Angeles
    assert (
        service._get_timezone_for_lat_lon(34.0522, -118.2437) == "America/Los_Angeles"
    )
