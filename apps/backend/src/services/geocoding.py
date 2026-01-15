"""Geocoding service for user location preferences."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_preferences import UserPreferences


logger = logging.getLogger(__name__)

# Rate limiting state for Nominatim API (1 req/sec per usage policy)
_last_geocode_time: float = 0.0
_geocode_lock = asyncio.Lock()


@lru_cache
def _should_use_redis_rate_limit() -> bool:
    """Check if Redis rate limiting is available."""
    try:
        from core.config import get_settings

        settings = get_settings()
        return bool(
            settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN
        )
    except Exception:
        return False


async def _rate_limit_geocoding() -> None:
    """Rate limit geocoding requests to 1 per second (Nominatim policy).

    Uses Redis if available, otherwise falls back to local rate limiting.
    """
    if _should_use_redis_rate_limit():
        # Use Redis-based rate limiting
        from upstash_ratelimit import FixedWindow, Ratelimit
        from upstash_redis import Redis

        from core.config import get_settings

        settings = get_settings()
        # Type checking: settings are guaranteed to be non-None by check above
        assert settings.UPSTASH_REDIS_REST_URL is not None
        assert settings.UPSTASH_REDIS_REST_TOKEN is not None

        redis = Redis(
            url=settings.UPSTASH_REDIS_REST_URL,
            token=settings.UPSTASH_REDIS_REST_TOKEN,
        )
        ratelimit = Ratelimit(
            redis=redis,
            limiter=FixedWindow(max_requests=1, window=1),  # 1 req/sec
            prefix="pantrypilot:geocoding",
        )

        # Use a fixed identifier for all geocoding requests
        response = ratelimit.limit("nominatim")
        result = await response if hasattr(response, "__await__") else response
        if not result.allowed:
            # Wait for the reset time
            wait_time = (result.reset - datetime.now(UTC).timestamp()) / 1000
            if wait_time > 0:
                await asyncio.sleep(wait_time)
    else:
        # Fall back to local rate limiting
        global _last_geocode_time
        async with _geocode_lock:
            now = asyncio.get_event_loop().time()
            time_since_last = now - _last_geocode_time
            if time_since_last < 1.0:
                await asyncio.sleep(1.0 - time_since_last)
            _last_geocode_time = asyncio.get_event_loop().time()


@dataclass
class GeocodingResult:
    """Result from geocoding service."""

    latitude: float
    longitude: float
    timezone: str
    display_name: str


class GeocodingService:
    """Service for geocoding user location fields.

    Uses Nominatim (OpenStreetMap) for free geocoding with rate limiting.
    """

    # Nominatim usage policy: https://operations.osmfoundation.org/policies/nominatim/
    # Required: User-Agent header, max 1 request per second
    NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
    USER_AGENT = "PantryPilot/1.0 (Meal Planning Assistant)"

    def __init__(self, db: AsyncSession) -> None:
        """Initialize geocoding service.

        Args:
            db: Database session
        """
        self.db = db

    async def geocode_location(
        self,
        city: str | None = None,
        state_or_region: str | None = None,
        postal_code: str | None = None,
        country: str | None = "US",
    ) -> GeocodingResult | None:
        """Geocode a location to latitude/longitude/timezone.

        Args:
            city: City name
            state_or_region: State/region/province
            postal_code: Postal/ZIP code
            country: ISO 3166-1 alpha-2 country code

        Returns:
            GeocodingResult or None if geocoding fails
        """
        # Build search query
        query_parts = []
        if city:
            query_parts.append(city)
        if state_or_region:
            query_parts.append(state_or_region)
        if postal_code:
            query_parts.append(postal_code)
        if country:
            query_parts.append(country)

        if not query_parts:
            logger.warning("Cannot geocode: no location fields provided")
            return None

        query = ", ".join(query_parts)

        try:
            # Rate limit to comply with Nominatim usage policy (1 req/sec)
            await _rate_limit_geocoding()

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.NOMINATIM_BASE_URL}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1,
                        "addressdetails": 1,
                    },
                    headers={"User-Agent": self.USER_AGENT},
                    timeout=10.0,
                )
                response.raise_for_status()
                results = response.json()

                if not results:
                    logger.warning(f"No geocoding results for query: {query}")
                    return None

                result = results[0]
                lat = float(result["lat"])
                lon = float(result["lon"])

                # Get timezone using lat/lon
                # For MVP, use a simple timezone mapping based on country
                # In production, consider using a proper timezone API
                timezone = self._get_timezone_for_country(country or "US")

                return GeocodingResult(
                    latitude=lat,
                    longitude=lon,
                    timezone=timezone,
                    display_name=result.get("display_name", query),
                )

        except httpx.HTTPError as e:
            logger.error(f"Geocoding HTTP error: {type(e).__name__}")
            return None
        except (ValueError, KeyError) as e:
            logger.error(f"Geocoding parse error: {type(e).__name__}")
            return None

    def _get_timezone_for_country(self, country: str) -> str:
        """Get default timezone for a country code.

        **MVP LIMITATION**: This uses a simplified country-level timezone mapping
        which is inaccurate for countries spanning multiple timezones (e.g., US).

        For accurate timezone resolution, a future enhancement should use a
        timezone lookup library (e.g., timezonefinder) based on lat/lon coordinates.
        This would provide correct timezones for all locations globally.

        **Impact**: Weather data and meal planning features may show times in the
        wrong timezone for users not in the default timezone for their country.
        For US users, times will be in Eastern time regardless of actual location.

        Args:
            country: ISO 3166-1 alpha-2 country code

        Returns:
            IANA timezone identifier (default for country, or UTC if unknown)

        TODO: Replace with proper timezone lookup using lat/lon (Issue #TBD)
        """
        # Basic mapping for common countries - defaults to most populous timezone
        timezone_map = {
            "US": "America/New_York",  # Eastern - covers ~47% of US population
            "CA": "America/Toronto",  # Eastern - covers ~62% of CA population
            "GB": "Europe/London",
            "FR": "Europe/Paris",
            "DE": "Europe/Berlin",
            "AU": "Australia/Sydney",  # Eastern - covers ~40% of AU population
            "NZ": "Pacific/Auckland",
        }
        return timezone_map.get(country.upper(), "UTC")

    async def update_geocoded_fields(
        self,
        preferences: UserPreferences,
    ) -> bool:
        """Update geocoded fields for user preferences.

        Args:
            preferences: User preferences model

        Returns:
            True if geocoding succeeded and fields were updated, False otherwise
        """
        # Only geocode if at least one location field is set
        # (aligns with geocode_location validation on line ~80)
        if not any(
            [
                preferences.city,
                preferences.state_or_region,
                preferences.postal_code,
                preferences.country,
            ]
        ):
            logger.debug(
                f"Skipping geocoding for user {preferences.user_id}: "
                f"no location fields provided"
            )
            return False

        result = await self.geocode_location(
            city=preferences.city,
            state_or_region=preferences.state_or_region,
            postal_code=preferences.postal_code,
            country=preferences.country,
        )

        if result is None:
            logger.warning(
                f"Geocoding failed for user {preferences.user_id} "
                f"(location fields provided but geocoding returned no results)"
            )
            return False

        # Update internal geocoded fields
        preferences.latitude = result.latitude
        preferences.longitude = result.longitude
        preferences.timezone = result.timezone
        preferences.geocoded_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(preferences)

        logger.info(
            f"Geocoded location for user {preferences.user_id}: "
            f"({result.latitude}, {result.longitude}), tz={result.timezone}"
        )

        return True

    def has_valid_location(self, preferences: UserPreferences) -> bool:
        """Check if preferences have a valid geocoded location.

        Args:
            preferences: User preferences model

        Returns:
            True if latitude and longitude are set
        """
        return preferences.latitude is not None and preferences.longitude is not None
