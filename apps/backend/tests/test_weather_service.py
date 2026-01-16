"""Unit tests for weather service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.weather import (
    WEATHER_CACHE_TTL,
    WeatherCacheEntry,
    _aggregate_weather_gov_periods,
    _cache_key,
    _format_location,
    _get_temperature_unit,
    _map_unit_label,
    _safe_float,
    _safe_int,
    _to_float,
    _weather_cache,
    clear_weather_cache,
    get_daily_forecast_for_user,
)


class TestHelperFunctions:
    """Test helper/utility functions."""

    def test_to_float_with_none(self) -> None:
        assert _to_float(None) is None

    def test_to_float_with_decimal(self) -> None:
        result = _to_float(Decimal("42.5"))
        assert result == 42.5
        assert isinstance(result, float)

    def test_to_float_with_float(self) -> None:
        result = _to_float(3.14)
        assert result == 3.14

    def test_get_temperature_unit_imperial(self) -> None:
        prefs = MagicMock()
        prefs.units = "imperial"
        assert _get_temperature_unit(prefs) == "fahrenheit"

    def test_get_temperature_unit_metric(self) -> None:
        prefs = MagicMock()
        prefs.units = "metric"
        assert _get_temperature_unit(prefs) == "celsius"

    def test_get_temperature_unit_default(self) -> None:
        prefs = MagicMock()
        prefs.units = None
        assert _get_temperature_unit(prefs) == "celsius"

    def test_map_unit_label_fahrenheit(self) -> None:
        assert _map_unit_label("fahrenheit") == "F"

    def test_map_unit_label_celsius(self) -> None:
        assert _map_unit_label("celsius") == "C"

    def test_format_location_full(self) -> None:
        prefs = MagicMock()
        prefs.city = "Boston"
        prefs.state_or_region = "MA"
        prefs.postal_code = "02101"
        prefs.country = "US"
        assert _format_location(prefs) == "Boston, MA, 02101, US"

    def test_format_location_partial(self) -> None:
        prefs = MagicMock()
        prefs.city = "Boston"
        prefs.state_or_region = None
        prefs.postal_code = None
        prefs.country = "US"
        assert _format_location(prefs) == "Boston, US"

    def test_format_location_empty(self) -> None:
        prefs = MagicMock()
        prefs.city = None
        prefs.state_or_region = None
        prefs.postal_code = None
        prefs.country = None
        assert _format_location(prefs) is None

    def test_format_location_whitespace_stripped(self) -> None:
        prefs = MagicMock()
        prefs.city = "  Boston  "
        prefs.state_or_region = ""
        prefs.postal_code = "02101"
        prefs.country = None
        assert _format_location(prefs) == "Boston, 02101"

    def test_cache_key_format(self) -> None:
        user_id = uuid4()
        key = _cache_key(
            user_id=user_id,
            latitude=42.3601,
            longitude=-71.0589,
            unit="fahrenheit",
            timezone="America/New_York",
        )
        assert str(user_id) in key
        assert "42.36010" in key
        assert "-71.05890" in key
        assert "fahrenheit" in key
        assert "America/New_York" in key

    def test_cache_key_auto_timezone(self) -> None:
        user_id = uuid4()
        key = _cache_key(
            user_id=user_id,
            latitude=0.0,
            longitude=0.0,
            unit="celsius",
            timezone=None,
        )
        assert "auto" in key


class TestSafeValueExtraction:
    """Test safe value extraction from arrays."""

    def test_safe_float_valid(self) -> None:
        assert _safe_float([1.0, 2.5, 3.0], 1) == 2.5

    def test_safe_float_index_out_of_range(self) -> None:
        assert _safe_float([1.0], 5) is None

    def test_safe_float_none_value(self) -> None:
        assert _safe_float([None, 2.0], 0) is None

    def test_safe_float_invalid_type(self) -> None:
        assert _safe_float(["not-a-number", 2.0], 0) is None

    def test_safe_int_valid(self) -> None:
        assert _safe_int([10, 20, 30], 1) == 20

    def test_safe_int_index_out_of_range(self) -> None:
        assert _safe_int([10], 5) is None

    def test_safe_int_none_value(self) -> None:
        assert _safe_int([None, 20], 0) is None

    def test_safe_int_invalid_type(self) -> None:
        assert _safe_int(["not-an-int", 20], 0) is None


class TestWeatherGovAggregation:
    """Test weather.gov period aggregation."""

    def test_aggregate_empty_periods(self) -> None:
        assert _aggregate_weather_gov_periods([]) == []

    def test_aggregate_daytime_period(self) -> None:
        periods = [
            {
                "startTime": "2026-01-16T06:00:00-05:00",
                "isDaytime": True,
                "temperature": 45,
                "probabilityOfPrecipitation": {"value": 20},
            }
        ]
        result = _aggregate_weather_gov_periods(periods)
        assert len(result) == 1
        assert result[0]["date"] == "2026-01-16"
        assert result[0]["high"] == 45
        assert result[0]["low"] is None
        assert result[0]["precip_probability"] == 20

    def test_aggregate_nighttime_period(self) -> None:
        periods = [
            {
                "startTime": "2026-01-16T18:00:00-05:00",
                "isDaytime": False,
                "temperature": 30,
                "probabilityOfPrecipitation": {"value": 10},
            }
        ]
        result = _aggregate_weather_gov_periods(periods)
        assert len(result) == 1
        assert result[0]["date"] == "2026-01-16"
        assert result[0]["high"] is None
        assert result[0]["low"] == 30

    def test_aggregate_combined_day_night(self) -> None:
        periods = [
            {
                "startTime": "2026-01-16T06:00:00-05:00",
                "isDaytime": True,
                "temperature": 50,
                "probabilityOfPrecipitation": {"value": 30},
            },
            {
                "startTime": "2026-01-16T18:00:00-05:00",
                "isDaytime": False,
                "temperature": 35,
                "probabilityOfPrecipitation": {"value": 40},
            },
        ]
        result = _aggregate_weather_gov_periods(periods)
        assert len(result) == 1
        assert result[0]["high"] == 50
        assert result[0]["low"] == 35
        assert result[0]["precip_probability"] == 40  # max of 30 and 40

    def test_aggregate_multiple_days_sorted(self) -> None:
        periods = [
            {
                "startTime": "2026-01-17T06:00:00-05:00",
                "isDaytime": True,
                "temperature": 55,
                "probabilityOfPrecipitation": {"value": 10},
            },
            {
                "startTime": "2026-01-16T06:00:00-05:00",
                "isDaytime": True,
                "temperature": 45,
                "probabilityOfPrecipitation": {"value": 20},
            },
        ]
        result = _aggregate_weather_gov_periods(periods)
        assert len(result) == 2
        assert result[0]["date"] == "2026-01-16"
        assert result[1]["date"] == "2026-01-17"

    def test_aggregate_limits_to_7_days(self) -> None:
        periods: list[dict[str, Any]] = []
        for i in range(10):
            periods.append(
                {
                    "startTime": f"2026-01-{16 + i:02d}T06:00:00-05:00",
                    "isDaytime": True,
                    "temperature": 40 + i,
                }
            )
        result = _aggregate_weather_gov_periods(periods)
        assert len(result) == 7

    def test_aggregate_skips_missing_start_time(self) -> None:
        periods: list[dict[str, Any]] = [
            {"isDaytime": True, "temperature": 50},  # No startTime
            {
                "startTime": "2026-01-16T06:00:00-05:00",
                "isDaytime": True,
                "temperature": 45,
            },
        ]
        result = _aggregate_weather_gov_periods(periods)
        assert len(result) == 1


class TestGetDailyForecastForUser:
    """Test the main forecast fetching function."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear the weather cache before each test."""
        clear_weather_cache()

    @pytest.mark.asyncio
    async def test_missing_preferences(self) -> None:
        """User with no preferences returns missing_location status."""
        mock_db = AsyncMock()
        user_id = uuid4()

        with patch(
            "services.weather.user_preferences_crud.get_by_user_id",
            return_value=None,
        ):
            result = await get_daily_forecast_for_user(mock_db, user_id=user_id)

        assert result["status"] == "missing_location"
        assert "city/ZIP" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_lat_lon(self) -> None:
        """User with preferences but no lat/lon returns missing_location."""
        mock_db = AsyncMock()
        user_id = uuid4()
        prefs = MagicMock()
        prefs.latitude = None
        prefs.longitude = None

        with patch(
            "services.weather.user_preferences_crud.get_by_user_id",
            return_value=prefs,
        ):
            result = await get_daily_forecast_for_user(mock_db, user_id=user_id)

        assert result["status"] == "missing_location"

    @pytest.mark.asyncio
    async def test_cache_hit(self) -> None:
        """Cached data is returned when within TTL."""
        mock_db = AsyncMock()
        user_id = uuid4()
        prefs = MagicMock()
        prefs.latitude = Decimal("42.3601")
        prefs.longitude = Decimal("-71.0589")
        prefs.timezone = "America/New_York"
        prefs.units = "imperial"
        prefs.city = "Boston"
        prefs.state_or_region = "MA"
        prefs.postal_code = None
        prefs.country = "US"

        cached_payload = {"status": "ok", "cached": True}
        cache_key = _cache_key(
            user_id=user_id,
            latitude=42.3601,
            longitude=-71.0589,
            unit="fahrenheit",
            timezone="America/New_York",
        )
        _weather_cache[cache_key] = WeatherCacheEntry(
            fetched_at=datetime.now(UTC),
            payload=cached_payload,
        )

        with patch(
            "services.weather.user_preferences_crud.get_by_user_id",
            return_value=prefs,
        ):
            result = await get_daily_forecast_for_user(mock_db, user_id=user_id)

        assert result["cached"] is True

    @pytest.mark.asyncio
    async def test_cache_expired(self) -> None:
        """Expired cache data triggers a new fetch."""
        mock_db = AsyncMock()
        user_id = uuid4()
        prefs = MagicMock()
        prefs.latitude = Decimal("42.3601")
        prefs.longitude = Decimal("-71.0589")
        prefs.timezone = "America/New_York"
        prefs.units = "imperial"
        prefs.city = "Boston"
        prefs.state_or_region = "MA"
        prefs.postal_code = None
        prefs.country = "US"

        cached_payload = {"status": "ok", "cached": True}
        cache_key = _cache_key(
            user_id=user_id,
            latitude=42.3601,
            longitude=-71.0589,
            unit="fahrenheit",
            timezone="America/New_York",
        )
        _weather_cache[cache_key] = WeatherCacheEntry(
            fetched_at=datetime.now(UTC) - WEATHER_CACHE_TTL - timedelta(minutes=1),
            payload=cached_payload,
        )

        fresh_payload: dict[str, Any] = {
            "status": "ok",
            "provider": "open-meteo",
            "fresh": True,
        }

        with (
            patch(
                "services.weather.user_preferences_crud.get_by_user_id",
                return_value=prefs,
            ),
            patch(
                "services.weather._fetch_open_meteo",
                return_value=fresh_payload,
            ),
        ):
            result = await get_daily_forecast_for_user(mock_db, user_id=user_id)

        assert result.get("fresh") is True

    @pytest.mark.asyncio
    async def test_open_meteo_success(self) -> None:
        """Successful Open-Meteo response is returned."""
        mock_db = AsyncMock()
        user_id = uuid4()
        prefs = MagicMock()
        prefs.latitude = Decimal("42.3601")
        prefs.longitude = Decimal("-71.0589")
        prefs.timezone = "America/New_York"
        prefs.units = None
        prefs.city = "Boston"
        prefs.state_or_region = "MA"
        prefs.postal_code = None
        prefs.country = None

        open_meteo_response = {
            "status": "ok",
            "provider": "open-meteo",
            "unit": "C",
            "location": "Boston, MA",
            "days": [{"date": "2026-01-16", "high": 5.0, "low": -2.0}],
        }

        with (
            patch(
                "services.weather.user_preferences_crud.get_by_user_id",
                return_value=prefs,
            ),
            patch(
                "services.weather._fetch_open_meteo",
                return_value=open_meteo_response,
            ),
        ):
            result = await get_daily_forecast_for_user(mock_db, user_id=user_id)

        assert result["status"] == "ok"
        assert result["provider"] == "open-meteo"

    @pytest.mark.asyncio
    async def test_weather_gov_fallback_for_us(self) -> None:
        """weather.gov is used as fallback for US locations."""
        mock_db = AsyncMock()
        user_id = uuid4()
        prefs = MagicMock()
        prefs.latitude = Decimal("42.3601")
        prefs.longitude = Decimal("-71.0589")
        prefs.timezone = "America/New_York"
        prefs.units = "imperial"
        prefs.city = "Boston"
        prefs.state_or_region = "MA"
        prefs.postal_code = None
        prefs.country = "US"

        open_meteo_error = {"status": "error", "provider": "open-meteo"}
        weather_gov_response = {
            "status": "ok",
            "provider": "weather.gov",
            "unit": "F",
            "location": "Boston, MA",
            "days": [{"date": "2026-01-16", "high": 45, "low": 30}],
        }

        with (
            patch(
                "services.weather.user_preferences_crud.get_by_user_id",
                return_value=prefs,
            ),
            patch(
                "services.weather._fetch_open_meteo",
                return_value=open_meteo_error,
            ),
            patch(
                "services.weather._fetch_weather_gov",
                return_value=weather_gov_response,
            ),
        ):
            result = await get_daily_forecast_for_user(mock_db, user_id=user_id)

        assert result["status"] == "ok"
        assert result["provider"] == "weather.gov"

    @pytest.mark.asyncio
    async def test_no_fallback_for_non_us(self) -> None:
        """weather.gov fallback is not used for non-US locations."""
        mock_db = AsyncMock()
        user_id = uuid4()
        prefs = MagicMock()
        prefs.latitude = Decimal("51.5074")
        prefs.longitude = Decimal("-0.1278")
        prefs.timezone = "Europe/London"
        prefs.units = None
        prefs.city = "London"
        prefs.state_or_region = None
        prefs.postal_code = None
        prefs.country = "UK"

        open_meteo_error = {"status": "error", "provider": "open-meteo"}

        with (
            patch(
                "services.weather.user_preferences_crud.get_by_user_id",
                return_value=prefs,
            ),
            patch(
                "services.weather._fetch_open_meteo",
                return_value=open_meteo_error,
            ),
            patch(
                "services.weather._fetch_weather_gov",
            ) as mock_weather_gov,
        ):
            result = await get_daily_forecast_for_user(mock_db, user_id=user_id)

        mock_weather_gov.assert_not_called()
        assert result["status"] == "error"
