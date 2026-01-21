"""Tools for web search and URL fetching."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from pydantic_ai import RunContext

from schemas.chat_streaming import MAX_SSE_EVENT_BYTES
from services.ai.markdown_extractor import MarkdownExtractionService
from services.chat_agent.deps import ChatAgentDeps
from services.web_search import search_web


logger = logging.getLogger(__name__)

# Maximum content size to avoid SSE payload limits
# Leave room for JSON overhead (url, status, message fields)
MAX_MARKDOWN_CONTENT_CHARS: int = MAX_SSE_EVENT_BYTES - 2000

# Lazy initialization for MarkdownExtractionService
_markdown_extractor: MarkdownExtractionService | None = None


def _get_markdown_extractor() -> MarkdownExtractionService:
    global _markdown_extractor
    if _markdown_extractor is None:
        _markdown_extractor = MarkdownExtractionService()
    return _markdown_extractor


async def tool_web_search(
    _ctx: RunContext[ChatAgentDeps], query: str
) -> dict[str, Any]:
    """Read-only web search tool (capped)."""
    outcome = await search_web(query)
    return {
        "status": outcome.status,
        "provider": outcome.provider,
        "results": [
            {
                "title": result.title,
                "url": result.url,
                "description": result.description,
            }
            for result in outcome.results
        ],
        "message": outcome.message,
    }


async def tool_fetch_url_as_markdown(
    _ctx: RunContext[ChatAgentDeps],
    url: str,
) -> dict[str, Any]:
    """Fetch a web page and convert it to readable Markdown.

    Use this tool when you need to read the content of a web page,
    especially recipe pages. The page will be fetched, cleaned of
    navigation and scripts, and converted to Markdown format that
    you can analyze.

    WORKFLOW TIP: After using web_search to find recipe URLs, use this
    tool to read the full recipe content. Then use suggest_recipe to
    create a saveable draft for the user.

    Args:
        url: The URL of the web page to fetch (from web_search results
             or provided by the user)

    Returns:
        Markdown content of the page that you can analyze to extract
        recipe details like title, ingredients, instructions, etc.
    """
    extractor = _get_markdown_extractor()

    try:
        markdown_content = await extractor.fetch_as_markdown(url)

        if not markdown_content:
            return {
                "status": "error",
                "url": url,
                "content": "",
                "message": "No content could be extracted from this URL.",
            }

        # Truncate content if too large to fit in SSE payload
        was_truncated = False
        if len(markdown_content) > MAX_MARKDOWN_CONTENT_CHARS:
            markdown_content = markdown_content[:MAX_MARKDOWN_CONTENT_CHARS]
            was_truncated = True
            logger.debug(
                f"Truncated markdown content from URL to "
                f"{MAX_MARKDOWN_CONTENT_CHARS} chars"
            )

        message = (
            f"Successfully fetched content from {url}. "
            "Analyze this to extract recipe details."
        )
        if was_truncated:
            message += (
                " Note: Content was truncated due to size limits. "
                "The most important recipe information is usually "
                "at the beginning of the page."
            )

        return {
            "status": "ok",
            "url": url,
            "content": markdown_content,
            "message": message,
        }

    except HTTPException as e:
        return {
            "status": "error",
            "url": url,
            "content": "",
            "message": str(e.detail),
        }
    except Exception as e:
        logger.error(f"Failed to fetch URL as Markdown: {e}")
        return {
            "status": "error",
            "url": url,
            "content": "",
            "message": (
                "Failed to fetch the URL. Please check if it's a valid web page."
            ),
        }
