"""Safe web fetch utility for chat tools."""

from __future__ import annotations

from dataclasses import dataclass

from services.ai.html_extractor import HTMLExtractionService


@dataclass(frozen=True)
class WebFetchResult:
    url: str
    content: str | None
    error: str | None = None


async def fetch_url_content(url: str) -> WebFetchResult:
    """Fetch and sanitize HTML content with safety limits."""
    extractor = HTMLExtractionService(timeout=10, max_size=1 * 1024 * 1024)
    try:
        content = await extractor.fetch_and_sanitize(url)
        return WebFetchResult(url=url, content=content)
    except Exception as exc:  # pragma: no cover - defensive
        return WebFetchResult(url=url, content=None, error=str(exc))
