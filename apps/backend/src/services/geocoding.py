"""Geocoding service for user location preferences."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_preferences import UserPreferences


logger = logging.getLogger(__name__)


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
            logger.error(f"Geocoding HTTP error for query '{query}': {e}")
            return None
        except (ValueError, KeyError) as e:
            logger.error(f"Geocoding parse error for query '{query}': {e}")
            return None

    def _get_timezone_for_country(self, country: str) -> str:
        """Get default timezone for a country code.

        This is a simplified mapping for MVP. In production, use a proper
        timezone API or library based on lat/lon.

        Args:
            country: ISO 3166-1 alpha-2 country code

        Returns:
            IANA timezone identifier
        """
        # Basic mapping for common countries
        timezone_map = {
            "US": "America/New_York",  # Default to Eastern
            "CA": "America/Toronto",
            "GB": "Europe/London",
            "FR": "Europe/Paris",
            "DE": "Europe/Berlin",
            "AU": "Australia/Sydney",
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
        # Only geocode if user-facing location fields are set
        if not any([preferences.city, preferences.postal_code]):
            logger.debug(
                f"Skipping geocoding for user {preferences.user_id}: "
                f"no city or postal code"
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
                f"Geocoding failed for user {preferences.user_id}, "
                f"location: {preferences.city}, {preferences.state_or_region}, "
                f"{preferences.postal_code}, {preferences.country}"
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
