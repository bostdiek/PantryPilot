"""Web search service using Brave Search API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from core.config import get_settings


logger = logging.getLogger(__name__)

BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
SEARCH_RESULT_LIMIT = 3


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    description: str | None


@dataclass(frozen=True)
class WebSearchOutcome:
    status: Literal["ok", "unconfigured", "error"]
    provider: Literal["brave", "duckduckgo", "none"]
    results: list[WebSearchResult]
    message: str | None = None


def _get_api_key() -> str | None:
    settings = get_settings()
    return settings.BRAVE_SEARCH_API_KEY


async def search_web(
    query: str, *, max_results: int = SEARCH_RESULT_LIMIT
) -> WebSearchOutcome:
    """Search the web using Brave Search API.

    Enforces an ingestion cap of 3 URLs by default.
    """
    max_results = min(max_results, SEARCH_RESULT_LIMIT)
    api_key = _get_api_key()
    if not api_key:
        return WebSearchOutcome(
            status="unconfigured",
            provider="none",
            results=[],
            message="Brave Search API key is not configured.",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                BRAVE_SEARCH_ENDPOINT,
                params={"q": query, "count": max_results},
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                },
            )
            response.raise_for_status()
            payload = response.json()

        results = _parse_brave_results(payload, max_results)
        return WebSearchOutcome(status="ok", provider="brave", results=results)
    except httpx.HTTPError as exc:
        logger.warning(
            "Brave search request failed: %s - %s",
            type(exc).__name__,
            str(exc),
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "Brave search parse failed: %s - %s",
            type(exc).__name__,
            str(exc),
        )

    return WebSearchOutcome(
        status="error",
        provider="brave",
        results=[],
        message="Unable to fetch search results right now.",
    )


def _parse_brave_results(
    payload: dict[str, Any], max_results: int
) -> list[WebSearchResult]:
    web = payload.get("web") or {}
    results_data = web.get("results") or []
    results: list[WebSearchResult] = []
    for item in results_data[:max_results]:
        url = item.get("url")
        title = item.get("title")
        if not url or not title:
            continue
        results.append(
            WebSearchResult(
                title=str(title),
                url=str(url),
                description=item.get("description"),
            )
        )
    return results
