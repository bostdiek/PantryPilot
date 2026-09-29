"""Unit tests for HTMLExtractionService (URL validation, fetch, sanitize)."""

from __future__ import annotations

import socket
from unittest.mock import Mock, patch

import httpx
import pytest
from bs4 import BeautifulSoup
from fastapi import HTTPException, status

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
@pytest.mark.parametrize("propagate_transient_errors", [False, True])
async def test_given_timeout_when_fetching_then_only_chat_rethrows_typed_error(
    propagate_transient_errors: bool,
) -> None:
    # Arrange
    extractor = HTMLExtractionService(
        propagate_transient_errors=propagate_transient_errors
    )
    error = httpx.ReadTimeout("PRIVATE_UPSTREAM_DETAILS")

    # Act and assert
    with patch.object(extractor, "_fetch_with_safe_redirects", side_effect=error):
        if propagate_transient_errors:
            with pytest.raises(httpx.ReadTimeout):
                await extractor._fetch_html("https://example.com/slow")
        else:
            with pytest.raises(HTTPException) as exc_info:
                await extractor._fetch_html("https://example.com/slow")
            assert exc_info.value.status_code == status.HTTP_408_REQUEST_TIMEOUT
            assert exc_info.value.detail == "Request timed out"
            assert "PRIVATE_UPSTREAM_DETAILS" not in str(exc_info.value.detail)


@pytest.mark.asyncio
@pytest.mark.parametrize("propagate_transient_errors", [False, True])
async def test_given_connection_error_when_fetching_then_only_chat_rethrows(
    propagate_transient_errors: bool,
) -> None:
    # Arrange
    extractor = HTMLExtractionService(
        propagate_transient_errors=propagate_transient_errors
    )
    error = httpx.ConnectError("PRIVATE_UPSTREAM_DETAILS")

    # Act and assert
    with patch.object(extractor, "_fetch_with_safe_redirects", side_effect=error):
        if propagate_transient_errors:
            with pytest.raises(httpx.ConnectError):
                await extractor._fetch_html("https://example.com/recipe")
        else:
            with pytest.raises(HTTPException) as exc_info:
                await extractor._fetch_html("https://example.com/recipe")
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert exc_info.value.detail == "Network error fetching URL"
            assert "PRIVATE_UPSTREAM_DETAILS" not in str(exc_info.value.detail)


@pytest.mark.asyncio
@pytest.mark.parametrize("propagate_transient_errors", [False, True])
async def test_given_retryable_http_response_when_fetching_then_only_chat_rethrows(
    propagate_transient_errors: bool,
) -> None:
    # Arrange
    extractor = HTMLExtractionService(
        propagate_transient_errors=propagate_transient_errors
    )
    response = httpx.Response(
        503, request=httpx.Request("GET", "https://example.com/recipe")
    )

    # Act and assert
    with patch.object(extractor, "_fetch_with_safe_redirects", return_value=response):
        if propagate_transient_errors:
            with pytest.raises(httpx.HTTPStatusError):
                await extractor._fetch_html("https://example.com/recipe")
        else:
            with pytest.raises(HTTPException) as exc_info:
                await extractor._fetch_html("https://example.com/recipe")
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


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


def test_remove_boilerplate_preserves_structural_containers() -> None:
    extractor = HTMLExtractionService()
    html = """
        <html>
            <body class="has-sidebar single-post">
                <main>
                    <article>
                        <div class="entry-content">
                            <h1>Creamy Mediterranean Chicken</h1>
                            <p>Chicken, cream, tomatoes, and spinach.</p>
                        </div>
                        <aside class="recipe-sidebar">
                            <p>Newsletter signup</p>
                        </aside>
                    </article>
                </main>
            </body>
        </html>
        """

    soup = BeautifulSoup(html, "html.parser")

    extractor._remove_boilerplate(soup)

    result = str(soup)
    assert "Creamy Mediterranean Chicken" in result
    assert "Chicken, cream, tomatoes, and spinach." in result
    assert "Newsletter signup" not in result
    assert soup.body is not None
