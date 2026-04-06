"""Web search service using Brave Search API."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from core.config import get_settings
from core.error_handler import get_correlation_id
from core.observability import (
    ProductTelemetryEventName,
    build_product_telemetry_attributes,
    get_tracer,
)


logger = logging.getLogger(__name__)
_tracer = get_tracer(__name__)

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
    request_id = get_correlation_id()
    started_at = time.monotonic()
    with _tracer.start_as_current_span("recipe_search") as span:
        for key, value in build_product_telemetry_attributes(
            event=ProductTelemetryEventName.RECIPE_SEARCH_SUBMITTED,
            feature_name="assistant_search",
            request_id=request_id,
            provider="brave" if api_key else "none",
            streamed=True,
        ).items():
            span.set_attribute(key, value)
        span.set_attribute("search.query_length", len(query))

        if not api_key:
            latency_ms = int((time.monotonic() - started_at) * 1000)
            for key, value in build_product_telemetry_attributes(
                event=ProductTelemetryEventName.RECIPE_SEARCH_SUBMITTED,
                feature_name="assistant_search",
                request_id=request_id,
                provider="none",
                success=False,
                latency_ms=latency_ms,
                error_type="unconfigured",
                streamed=True,
            ).items():
                span.set_attribute(key, value)
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
            latency_ms = int((time.monotonic() - started_at) * 1000)
            for key, value in build_product_telemetry_attributes(
                event=ProductTelemetryEventName.RECIPE_SEARCH_RESULT_CLICKED,
                feature_name="assistant_search",
                request_id=request_id,
                provider="brave",
                success=True,
                latency_ms=latency_ms,
                tool_count=len(results),
                streamed=True,
            ).items():
                span.set_attribute(key, value)
            return WebSearchOutcome(status="ok", provider="brave", results=results)
        except httpx.HTTPError as exc:
            logger.warning(
                "Brave search request failed: %s - %s",
                type(exc).__name__,
                str(exc),
            )
            error_type = type(exc).__name__
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "Brave search parse failed: %s - %s",
                type(exc).__name__,
                str(exc),
            )
            error_type = type(exc).__name__

        latency_ms = int((time.monotonic() - started_at) * 1000)
        for key, value in build_product_telemetry_attributes(
            event=ProductTelemetryEventName.RECIPE_SEARCH_SUBMITTED,
            feature_name="assistant_search",
            request_id=request_id,
            provider="brave",
            success=False,
            latency_ms=latency_ms,
            error_type=error_type,
            streamed=True,
        ).items():
            span.set_attribute(key, value)

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
