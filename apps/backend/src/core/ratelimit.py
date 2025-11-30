"""Rate limiting configuration using Upstash Redis.

Provides distributed rate limiting for API endpoints using Upstash's
serverless Redis service. Falls back to allowing requests if Upstash
is not configured (development/test environments).
"""

from __future__ import annotations

import logging
import time
import uuid
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request, status

from core.config import Settings, get_settings


if TYPE_CHECKING:
    from upstash_ratelimit import Ratelimit

logger = logging.getLogger(__name__)

# Paths that bypass rate limiting (health checks, etc.)
RATE_LIMIT_BYPASS_PATHS: set[str] = {
    "/api/v1/health",
    "/api/v1/health/",
    "/health",
    "/health/",
}


@lru_cache
def get_ratelimiter() -> Ratelimit | None:
    """Create and cache the rate limiter instance.

    Returns None if Upstash is not configured, allowing the application
    to run without rate limiting in development/test environments.
    """
    # Import here to avoid import errors if upstash packages aren't used
    from upstash_ratelimit import Ratelimit, SlidingWindow
    from upstash_redis import Redis

    settings = get_settings()

    if not settings.UPSTASH_REDIS_REST_URL or not settings.UPSTASH_REDIS_REST_TOKEN:
        logger.warning(
            "Upstash Redis not configured. Rate limiting is disabled. "
            "Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN to enable."
        )
        return None

    try:
        redis = Redis(
            url=settings.UPSTASH_REDIS_REST_URL,
            token=settings.UPSTASH_REDIS_REST_TOKEN,
        )
        ratelimit = Ratelimit(
            redis=redis,
            limiter=SlidingWindow(
                max_requests=settings.RATE_LIMIT_REQUESTS,
                window=settings.RATE_LIMIT_WINDOW_SECONDS,
            ),
            prefix="pantrypilot:ratelimit",
        )
        logger.info(
            "Rate limiting enabled: %d requests per %d seconds",
            settings.RATE_LIMIT_REQUESTS,
            settings.RATE_LIMIT_WINDOW_SECONDS,
        )
        return ratelimit
    except Exception as e:
        logger.error("Failed to initialize rate limiter: %s", e)
        return None


def _get_client_identifier(request: Request) -> str:
    """Extract client identifier from request for rate limiting.

    Uses X-Forwarded-For header if present (for reverse proxy setups),
    otherwise falls back to the direct client IP.
    """
    # Check for forwarded IP (common in containerized/proxy setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()

    # Fall back to direct client IP
    if request.client and request.client.host:
        return request.client.host

    # If no IP can be determined, generate a unique identifier per request
    # to avoid rate limit bucket collision between unidentifiable clients
    return f"unknown:{uuid.uuid4()}"


async def check_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """FastAPI dependency to enforce rate limits on endpoints.

    Raises HTTPException with 429 status if rate limit is exceeded.
    Bypasses rate limiting for health check endpoints and when
    Upstash is not configured.

    Usage:
        @router.post("/login", dependencies=[Depends(check_rate_limit)])
        async def login(...): ...
    """
    # Bypass rate limiting for health checks and admin paths
    path = request.url.path
    if path in RATE_LIMIT_BYPASS_PATHS:
        return

    ratelimiter = get_ratelimiter()
    if ratelimiter is None:
        # Rate limiting not configured; allow request
        return

    identifier = _get_client_identifier(request)

    try:
        response = ratelimiter.limit(identifier)

        if not response.allowed:
            # Calculate reset time in seconds from now
            current_time_ms = int(time.time() * 1000)
            reset_in_seconds = max(1, (response.reset - current_time_ms) // 1000)
            logger.warning(
                "Rate limit exceeded for %s on %s. Reset in %d seconds.",
                identifier,
                path,
                reset_in_seconds,
            )
            # Use the same calculation for Retry-After header
            retry_after = reset_in_seconds
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_REQUESTS),
                    "X-RateLimit-Remaining": str(response.remaining),
                },
            )
    except HTTPException:
        # Re-raise HTTP exceptions (including our 429)
        raise
    except Exception as e:
        # Log but don't block requests if rate limiting fails
        logger.error("Rate limit check failed: %s", e)
