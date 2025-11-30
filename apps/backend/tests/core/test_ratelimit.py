"""Tests for rate limiting functionality.

Tests cover:
- Graceful degradation when Redis fails
- 429 response when rate limit exceeded
- Client identifier extraction from various sources
"""

from __future__ import annotations

import time
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from core.ratelimit import _get_client_identifier, check_rate_limit


class TestCheckRateLimit:
    """Tests for the check_rate_limit dependency."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_allows_request_on_redis_error(self) -> None:
        """Verify requests proceed when rate limiter raises exception.

        This tests graceful degradation - when Redis fails, requests should
        still be allowed through rather than blocking all traffic.
        """
        # Setup mock request
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.headers.get.return_value = "192.168.1.1"
        mock_request.client.host = "192.168.1.1"

        # Setup mock settings
        mock_settings = MagicMock()
        mock_settings.RATE_LIMIT_REQUESTS = 10

        # Setup mock ratelimiter that raises exception
        mock_ratelimiter = MagicMock()
        mock_ratelimiter.limit.side_effect = Exception("Redis connection failed")

        with patch("core.ratelimit.get_ratelimiter", return_value=mock_ratelimiter):
            # Should not raise - graceful degradation allows request through
            await check_rate_limit(mock_request, mock_settings)

            # Verify limit was attempted
            mock_ratelimiter.limit.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_rate_limit_returns_429_when_exceeded(self) -> None:
        """Verify 429 response when rate limit exceeded."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.headers.get.return_value = None
        mock_request.client.host = "192.168.1.1"

        mock_settings = MagicMock()
        mock_settings.RATE_LIMIT_REQUESTS = 10

        # Mock response indicating limit exceeded
        mock_response = MagicMock()
        mock_response.allowed = False
        mock_response.remaining = 0
        mock_response.reset = int(time.time() * 1000) + 30000  # 30 seconds from now

        mock_ratelimiter = MagicMock()
        mock_ratelimiter.limit.return_value = mock_response

        with patch("core.ratelimit.get_ratelimiter", return_value=mock_ratelimiter):
            with pytest.raises(HTTPException) as exc_info:
                await check_rate_limit(mock_request, mock_settings)

            assert exc_info.value.status_code == 429
            assert exc_info.value.headers is not None
            assert "Retry-After" in exc_info.value.headers
            assert "X-RateLimit-Limit" in exc_info.value.headers
            assert "X-RateLimit-Remaining" in exc_info.value.headers

    @pytest.mark.asyncio
    async def test_check_rate_limit_bypasses_health_endpoints(self) -> None:
        """Verify health check endpoints bypass rate limiting."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/health"

        mock_settings = MagicMock()

        # Should not call get_ratelimiter for health endpoints
        with patch("core.ratelimit.get_ratelimiter") as mock_get_ratelimiter:
            await check_rate_limit(mock_request, mock_settings)
            mock_get_ratelimiter.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_rate_limit_allows_when_not_configured(self) -> None:
        """Verify requests proceed when rate limiting is not configured."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/auth/login"

        mock_settings = MagicMock()

        # Rate limiter returns None (not configured)
        with patch("core.ratelimit.get_ratelimiter", return_value=None):
            # Should not raise - allows request through
            await check_rate_limit(mock_request, mock_settings)


class TestGetClientIdentifier:
    """Tests for client identifier extraction."""

    def test_get_client_identifier_uses_forwarded_for(self) -> None:
        """Verify X-Forwarded-For header is used when present."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "10.0.0.1, 192.168.1.1"

        result = _get_client_identifier(mock_request)

        assert result == "10.0.0.1"  # First IP in chain

    def test_get_client_identifier_uses_forwarded_for_single_ip(self) -> None:
        """Verify single X-Forwarded-For IP is handled correctly."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "10.0.0.1"

        result = _get_client_identifier(mock_request)

        assert result == "10.0.0.1"

    def test_get_client_identifier_uses_client_host(self) -> None:
        """Verify client.host is used when no X-Forwarded-For."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = None
        mock_request.client.host = "192.168.1.100"

        result = _get_client_identifier(mock_request)

        assert result == "192.168.1.100"

    def test_get_client_identifier_returns_uuid_when_no_client(self) -> None:
        """Verify UUID is generated when client is None."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = None
        mock_request.client = None  # No client info

        result = _get_client_identifier(mock_request)

        assert result.startswith("unknown:")
        # Verify it's a valid UUID format
        uuid_part = result.split(":")[1]
        uuid.UUID(uuid_part)  # Will raise if invalid

    def test_get_client_identifier_returns_uuid_when_no_host(self) -> None:
        """Verify UUID is generated when client.host is None."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = None
        mock_request.client = MagicMock()
        mock_request.client.host = None

        result = _get_client_identifier(mock_request)

        assert result.startswith("unknown:")
        # Verify it's a valid UUID format
        uuid_part = result.split(":")[1]
        uuid.UUID(uuid_part)  # Will raise if invalid

    def test_get_client_identifier_strips_whitespace(self) -> None:
        """Verify whitespace is stripped from X-Forwarded-For IPs."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "  10.0.0.1  , 192.168.1.1"

        result = _get_client_identifier(mock_request)

        assert result == "10.0.0.1"  # Whitespace stripped
