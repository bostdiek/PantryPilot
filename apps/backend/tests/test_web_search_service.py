"""Unit tests for web search service."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from services.web_search import (
    SEARCH_RESULT_LIMIT,
    WebSearchOutcome,
    WebSearchResult,
    _parse_brave_results,
    search_web,
)


class TestParseBraveResults:
    """Test Brave Search result parsing."""

    def test_parse_empty_payload(self) -> None:
        payload: dict[str, Any] = {}
        results = _parse_brave_results(payload, max_results=3)
        assert results == []

    def test_parse_missing_web_key(self) -> None:
        payload: dict[str, Any] = {"other": "data"}
        results = _parse_brave_results(payload, max_results=3)
        assert results == []

    def test_parse_empty_results(self) -> None:
        payload: dict[str, Any] = {"web": {"results": []}}
        results = _parse_brave_results(payload, max_results=3)
        assert results == []

    def test_parse_single_result(self) -> None:
        payload = {
            "web": {
                "results": [
                    {
                        "title": "Test Recipe",
                        "url": "https://example.com/recipe",
                        "description": "A delicious test recipe",
                    }
                ]
            }
        }
        results = _parse_brave_results(payload, max_results=3)
        assert len(results) == 1
        assert results[0].title == "Test Recipe"
        assert results[0].url == "https://example.com/recipe"
        assert results[0].description == "A delicious test recipe"

    def test_parse_multiple_results(self) -> None:
        payload = {
            "web": {
                "results": [
                    {"title": f"Recipe {i}", "url": f"https://example.com/{i}"}
                    for i in range(5)
                ]
            }
        }
        results = _parse_brave_results(payload, max_results=3)
        assert len(results) == 3  # Respects max_results

    def test_parse_skips_missing_url(self) -> None:
        payload = {
            "web": {
                "results": [
                    {"title": "No URL Recipe"},
                    {
                        "title": "Valid Recipe",
                        "url": "https://example.com/valid",
                    },
                ]
            }
        }
        results = _parse_brave_results(payload, max_results=3)
        assert len(results) == 1
        assert results[0].title == "Valid Recipe"

    def test_parse_skips_missing_title(self) -> None:
        payload = {
            "web": {
                "results": [
                    {"url": "https://example.com/no-title"},
                    {
                        "title": "Has Title",
                        "url": "https://example.com/has-title",
                    },
                ]
            }
        }
        results = _parse_brave_results(payload, max_results=3)
        assert len(results) == 1
        assert results[0].title == "Has Title"

    def test_parse_handles_none_description(self) -> None:
        payload = {
            "web": {
                "results": [
                    {
                        "title": "Recipe",
                        "url": "https://example.com/recipe",
                        # description is missing
                    }
                ]
            }
        }
        results = _parse_brave_results(payload, max_results=3)
        assert len(results) == 1
        assert results[0].description is None


class TestSearchWeb:
    """Test the main search_web function."""

    @pytest.mark.asyncio
    async def test_unconfigured_returns_status(self) -> None:
        """When API key is not configured, return unconfigured status."""
        with patch("services.web_search._get_api_key", return_value=None):
            result = await search_web("pasta recipes")

        assert result.status == "unconfigured"
        assert result.provider == "none"
        assert result.results == []
        assert "not configured" in (result.message or "")

    @pytest.mark.asyncio
    async def test_max_results_capped(self) -> None:
        """max_results is capped at SEARCH_RESULT_LIMIT."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"web": {"results": []}}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("services.web_search._get_api_key", return_value="test-key"),
            patch("httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            # Request more than the limit
            await search_web("test", max_results=10)

            # Verify the capped value was used
            call_args = mock_client.return_value.__aenter__.return_value.get.call_args
            assert call_args[1]["params"]["count"] == SEARCH_RESULT_LIMIT

    @pytest.mark.asyncio
    async def test_successful_search(self) -> None:
        """Successful API response returns ok status with results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Pasta Recipe",
                        "url": "https://example.com/pasta",
                        "description": "Easy pasta recipe",
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch("services.web_search._get_api_key", return_value="test-key"),
            patch("httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await search_web("pasta recipes")

        assert result.status == "ok"
        assert result.provider == "brave"
        assert len(result.results) == 1
        assert result.results[0].title == "Pasta Recipe"

    @pytest.mark.asyncio
    async def test_http_error_returns_error_status(self) -> None:
        """HTTP errors are handled gracefully."""
        with (
            patch("services.web_search._get_api_key", return_value="test-key"),
            patch("httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                httpx.HTTPError("Connection failed")
            )

            result = await search_web("test query")

        assert result.status == "error"
        assert result.provider == "brave"
        assert result.results == []
        assert "Unable to fetch" in (result.message or "")

    @pytest.mark.asyncio
    async def test_parse_error_returns_error_status(self) -> None:
        """JSON parse errors are handled gracefully."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()

        with (
            patch("services.web_search._get_api_key", return_value="test-key"),
            patch("httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await search_web("test query")

        assert result.status == "error"
        assert result.provider == "brave"

    @pytest.mark.asyncio
    async def test_correct_headers_sent(self) -> None:
        """Verify correct headers are sent to Brave API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"web": {"results": []}}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("services.web_search._get_api_key", return_value="my-api-key"),
            patch("httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            await search_web("test query")

            call_args = mock_client.return_value.__aenter__.return_value.get.call_args
            headers = call_args[1]["headers"]
            assert headers["Accept"] == "application/json"
            assert headers["X-Subscription-Token"] == "my-api-key"


class TestDataclasses:
    """Test dataclass definitions."""

    def test_web_search_result_creation(self) -> None:
        result = WebSearchResult(
            title="Test",
            url="https://example.com",
            description="A test result",
        )
        assert result.title == "Test"
        assert result.url == "https://example.com"
        assert result.description == "A test result"

    def test_web_search_result_no_description(self) -> None:
        result = WebSearchResult(
            title="Test",
            url="https://example.com",
            description=None,
        )
        assert result.description is None

    def test_web_search_outcome_ok(self) -> None:
        outcome = WebSearchOutcome(
            status="ok",
            provider="brave",
            results=[
                WebSearchResult(
                    title="Test", url="https://example.com", description=None
                )
            ],
        )
        assert outcome.status == "ok"
        assert outcome.message is None

    def test_web_search_outcome_error_with_message(self) -> None:
        outcome = WebSearchOutcome(
            status="error",
            provider="brave",
            results=[],
            message="Something went wrong",
        )
        assert outcome.status == "error"
        assert outcome.message == "Something went wrong"
