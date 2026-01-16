"""Weather tool service (daily-only forecast)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from crud.user_preferences import user_preferences_crud
from models.user_preferences import UserPreferences


logger = logging.getLogger(__name__)

OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_GOV_POINTS_URL = "https://api.weather.gov/points"
WEATHER_CACHE_TTL = timedelta(minutes=20)
WEATHER_MAX_DAYS = 7


@dataclass(frozen=True)
class WeatherCacheEntry:
    fetched_at: datetime
    payload: dict[str, Any]


_weather_cache: dict[str, WeatherCacheEntry] = {}


def _cache_key(
    *, user_id: UUID, latitude: float, longitude: float, unit: str, timezone: str | None
) -> str:
    return f"{user_id}:{latitude:.5f}:{longitude:.5f}:{unit}:{timezone or 'auto'}"


def _format_location(preferences: UserPreferences) -> str | None:
    parts = [
        preferences.city,
        preferences.state_or_region,
        preferences.postal_code,
        preferences.country,
    ]
    cleaned = [part.strip() for part in parts if part and part.strip()]
    return ", ".join(cleaned) if cleaned else None


def _to_float(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def _get_temperature_unit(preferences: UserPreferences) -> str:
    if preferences.units and preferences.units.lower() == "imperial":
        return "fahrenheit"
    return "celsius"


def _map_unit_label(unit: str) -> str:
    return "F" if unit == "fahrenheit" else "C"


async def get_daily_forecast_for_user(
    db: AsyncSession,
    *,
    user_id: UUID,
) -> dict[str, Any]:
    """Fetch daily forecast data for the user's saved location."""
    preferences = await user_preferences_crud.get_by_user_id(db, user_id)
    if preferences is None:
        return {
            "status": "missing_location",
            "message": "What city/ZIP should I use for meal-planning weather?",
        }

    latitude = _to_float(preferences.latitude)
    longitude = _to_float(preferences.longitude)
    timezone = preferences.timezone or "auto"
    if latitude is None or longitude is None:
        return {
            "status": "missing_location",
            "message": "What city/ZIP should I use for meal-planning weather?",
        }

    unit = _get_temperature_unit(preferences)
    cache_key = _cache_key(
        user_id=user_id,
        latitude=latitude,
        longitude=longitude,
        unit=unit,
        timezone=timezone,
    )
    cached = _weather_cache.get(cache_key)
    now = datetime.now(UTC)
    if cached and now - cached.fetched_at < WEATHER_CACHE_TTL:
        return cached.payload

    location_label = _format_location(preferences)

    payload = await _fetch_open_meteo(
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        unit=unit,
        location_label=location_label,
    )

    if payload.get("status") != "ok":
        country = (preferences.country or "").upper()
        if country in {"US", "USA"}:
            fallback = await _fetch_weather_gov(
                latitude=latitude,
                longitude=longitude,
                location_label=location_label,
            )
            if fallback.get("status") == "ok":
                payload = fallback

    _weather_cache[cache_key] = WeatherCacheEntry(fetched_at=now, payload=payload)
    return payload


async def _fetch_open_meteo(
    *,
    latitude: float,
    longitude: float,
    timezone: str,
    unit: str,
    location_label: str | None,
) -> dict[str, Any]:
    try:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": (
                "temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            ),
            "forecast_days": WEATHER_MAX_DAYS,
            "timezone": timezone,
            "temperature_unit": unit,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OPEN_METEO_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        daily = data.get("daily") or {}
        dates = daily.get("time") or []
        highs = daily.get("temperature_2m_max") or []
        lows = daily.get("temperature_2m_min") or []
        precip = daily.get("precipitation_probability_max") or []

        days: list[dict[str, Any]] = []
        for idx, date in enumerate(dates[:WEATHER_MAX_DAYS]):
            days.append(
                {
                    "date": date,
                    "high": _safe_float(highs, idx),
                    "low": _safe_float(lows, idx),
                    "precip_probability": _safe_int(precip, idx),
                }
            )

        return {
            "status": "ok",
            "provider": "open-meteo",
            "unit": _map_unit_label(unit),
            "location": location_label,
            "days": days,
        }
    except httpx.HTTPError as exc:
        logger.warning("Open-Meteo request failed: %s", type(exc).__name__)
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Open-Meteo response parse failed: %s", type(exc).__name__)

    return {
        "status": "error",
        "provider": "open-meteo",
        "message": "Unable to fetch daily forecast right now.",
    }


async def _fetch_weather_gov(
    *,
    latitude: float,
    longitude: float,
    location_label: str | None,
) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            points = await client.get(
                f"{WEATHER_GOV_POINTS_URL}/{latitude:.4f},{longitude:.4f}"
            )
            points.raise_for_status()
            points_data = points.json()

            forecast_url = (
                points_data.get("properties", {}).get("forecast")
                if points_data
                else None
            )
            if not forecast_url:
                raise ValueError("Missing forecast URL")

            forecast_response = await client.get(forecast_url)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()

        periods = forecast_data.get("properties", {}).get("periods", [])
        days = _aggregate_weather_gov_periods(periods)
        if not days:
            raise ValueError("No forecast periods")

        return {
            "status": "ok",
            "provider": "weather.gov",
            "unit": "F",
            "location": location_label,
            "days": days,
        }
    except httpx.HTTPError as exc:
        logger.warning("weather.gov request failed: %s", type(exc).__name__)
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("weather.gov response parse failed: %s", type(exc).__name__)

    return {
        "status": "error",
        "provider": "weather.gov",
        "message": "Unable to fetch daily forecast right now.",
    }


def _aggregate_weather_gov_periods(
    periods: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    days: dict[str, dict[str, Any]] = {}
    for period in periods:
        start_time = period.get("startTime")
        if not start_time:
            continue
        date_key = start_time.split("T")[0]
        entry = days.setdefault(
            date_key,
            {"date": date_key, "high": None, "low": None, "precip_probability": None},
        )
        is_daytime = period.get("isDaytime")
        temp = period.get("temperature")
        precip = period.get("probabilityOfPrecipitation", {}).get("value")
        if precip is not None:
            entry["precip_probability"] = max(
                entry.get("precip_probability") or 0, precip
            )
        if is_daytime and temp is not None:
            entry["high"] = temp
        elif not is_daytime and temp is not None:
            entry["low"] = temp

    results = list(days.values())
    results.sort(key=lambda item: item["date"])
    return results[:WEATHER_MAX_DAYS]


def _safe_float(values: list[object], idx: int) -> float | None:
    try:
        value = values[idx]
    except IndexError:
        return None
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(values: list[object], idx: int) -> int | None:
    try:
        value = values[idx]
    except IndexError:
        return None
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
