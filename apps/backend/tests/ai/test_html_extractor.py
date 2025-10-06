"""Unit tests for HTMLExtractionService (URL validation, fetch, sanitize)."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from services.ai.html_extractor import HTMLExtractionService


def test_validate_url_good_and_bad():
    extractor = HTMLExtractionService()
    extractor._validate_url("https://example.com/recipe")
    extractor._validate_url("http://example.com/recipe")

    from fastapi import HTTPException

    bad_urls = [
        "not-a-url",
        "ftp://example.com",
        "http://localhost/recipe",
        "javascript:alert('x')",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
    ]
    for u in bad_urls:
        with pytest.raises(HTTPException):
            extractor._validate_url(u)


@pytest.mark.asyncio
async def test_fetch_timeout():
    extractor = HTMLExtractionService(timeout=1)
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = Exception(
            "Timeout"
        )
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await extractor.fetch_and_sanitize("https://example.com/slow")


@pytest.mark.asyncio
async def test_successful_fetch(mock_recipe_html):
    extractor = HTMLExtractionService()
    with patch.object(
        HTMLExtractionService, "_fetch_html", return_value=mock_recipe_html
    ):
        result = await extractor.fetch_and_sanitize("https://example.com/recipe")
    assert "Chicken Parmesan" in result
    assert "alert('evil script')" not in result


@pytest.mark.asyncio
async def test_http_error():
    extractor = HTMLExtractionService()
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = Exception("404 Not Found")
        mock_async = mock_client.return_value.__aenter__.return_value
        mock_async.get.return_value = mock_resp
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await extractor.fetch_and_sanitize("https://example.com/missing")


@pytest.mark.asyncio
async def test_empty_response():
    extractor = HTMLExtractionService()
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = Mock()
        mock_resp.text = ""
        mock_resp.content = b""
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.raise_for_status = Mock()
        mock_async = mock_client.return_value.__aenter__.return_value
        mock_async.get.return_value = mock_resp
        result = await extractor.fetch_and_sanitize("https://example.com/empty")
        assert result == ""
