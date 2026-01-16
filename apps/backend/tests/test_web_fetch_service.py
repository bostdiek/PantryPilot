"""Unit tests for web fetch service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.web_fetch import WebFetchResult, fetch_url_content


class TestWebFetchResult:
    """Test WebFetchResult dataclass."""

    def test_success_result(self) -> None:
        result = WebFetchResult(
            url="https://example.com",
            content="<html>Test content</html>",
        )
        assert result.url == "https://example.com"
        assert result.content == "<html>Test content</html>"
        assert result.error is None

    def test_error_result(self) -> None:
        result = WebFetchResult(
            url="https://example.com",
            content=None,
            error="Connection timeout",
        )
        assert result.url == "https://example.com"
        assert result.content is None
        assert result.error == "Connection timeout"


class TestFetchUrlContent:
    """Test fetch_url_content function."""

    @pytest.mark.asyncio
    async def test_successful_fetch(self) -> None:
        """Successful fetch returns content."""
        mock_extractor = AsyncMock()
        mock_extractor.fetch_and_sanitize.return_value = "Sanitized content"

        with patch(
            "services.web_fetch.HTMLExtractionService",
            return_value=mock_extractor,
        ):
            result = await fetch_url_content("https://example.com/recipe")

        assert result.url == "https://example.com/recipe"
        assert result.content == "Sanitized content"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_extractor_called_with_url(self) -> None:
        """HTMLExtractionService is called with the provided URL."""
        mock_extractor = AsyncMock()
        mock_extractor.fetch_and_sanitize.return_value = "Content"

        with patch(
            "services.web_fetch.HTMLExtractionService",
            return_value=mock_extractor,
        ):
            await fetch_url_content("https://recipes.example.com/pasta")

        mock_extractor.fetch_and_sanitize.assert_called_once_with(
            "https://recipes.example.com/pasta"
        )

    @pytest.mark.asyncio
    async def test_extractor_config(self) -> None:
        """HTMLExtractionService is configured with appropriate limits."""
        mock_extractor = AsyncMock()
        mock_extractor.fetch_and_sanitize.return_value = "Content"

        with patch(
            "services.web_fetch.HTMLExtractionService",
            return_value=mock_extractor,
        ) as mock_service_class:
            await fetch_url_content("https://example.com")

        mock_service_class.assert_called_once_with(
            timeout=10,
            max_size=1 * 1024 * 1024,  # 1MB
        )

    @pytest.mark.asyncio
    async def test_exception_returns_error(self) -> None:
        """Exceptions are caught and returned as error."""
        mock_extractor = AsyncMock()
        mock_extractor.fetch_and_sanitize.side_effect = Exception("Network error")

        with patch(
            "services.web_fetch.HTMLExtractionService",
            return_value=mock_extractor,
        ):
            result = await fetch_url_content("https://example.com")

        assert result.url == "https://example.com"
        assert result.content is None
        assert result.error == "Network error"

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self) -> None:
        """Timeout errors are handled gracefully."""
        mock_extractor = AsyncMock()
        mock_extractor.fetch_and_sanitize.side_effect = TimeoutError(
            "Request timed out"
        )

        with patch(
            "services.web_fetch.HTMLExtractionService",
            return_value=mock_extractor,
        ):
            result = await fetch_url_content("https://slow-site.example.com")

        assert result.content is None
        assert "timed out" in (result.error or "")
