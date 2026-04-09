"""Unit tests for HTMLExtractionService (URL validation, fetch, sanitize)."""

from __future__ import annotations

import socket
from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi import HTTPException

from services.ai.html_extractor import HTMLExtractionService


@pytest.fixture
def mock_recipe_html() -> str:
    return """
        <html>
            <body>
                <article class="recipe">
                    <h1>Chicken Parmesan</h1>
                    <p>Crispy chicken with marinara.</p>
                    <script>alert('evil script')</script>
                </article>
            </body>
        </html>
        """


def test_validate_url_good_and_bad(monkeypatch: pytest.MonkeyPatch):
    def fake_getaddrinfo(host: str, *args: object, **kwargs: object):
        # Keep localhost resolving to loopback so validation still blocks it
        if host == "localhost":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    extractor = HTMLExtractionService()
    extractor._validate_url("https://example.com/recipe")
    extractor._validate_url("http://example.com/recipe")

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


def test_validate_url_allows_globally_routable_reserved_ipv6_answer(
    monkeypatch: pytest.MonkeyPatch,
):
    extractor = HTMLExtractionService()

    def fake_getaddrinfo(host: str, *args: object, **kwargs: object):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("23.185.0.4", 0)),
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                6,
                "",
                ("aaaa:2620:12a:8001::4", 0, 0, 0),
            ),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    extractor._validate_url("https://alberscorn.com/sweet-corn-bread/")


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
async def test_fetch_html_reports_bot_protection_challenge() -> None:
    extractor = HTMLExtractionService()
    request = httpx.Request("GET", "https://www.ambitiouskitchen.com/recipe")
    response = httpx.Response(
        403,
        request=request,
        headers={
            "content-type": "text/html; charset=UTF-8",
            "server": "cloudflare",
            "cf-mitigated": "challenge",
        },
        text="Just a moment...",
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_async = mock_client.return_value.__aenter__.return_value
        mock_async.get.return_value = response

        with pytest.raises(HTTPException) as exc:
            await extractor._fetch_html(
                "https://www.ambitiouskitchen.com/lemon-blueberry-sweet-rolls/"
            )

    assert exc.value.status_code == 422
    assert "blocking automated access" in str(exc.value.detail)


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
