"""High-level service for fetching URLs and returning Markdown."""

from __future__ import annotations

import logging

from services.ai.html_extractor import HTMLExtractionService
from services.ai.markdown_converter import MarkdownConversionService


logger = logging.getLogger(__name__)


class MarkdownExtractionService:
    """Fetch URLs and convert to clean Markdown for LLM processing."""

    def __init__(
        self,
        html_extractor: HTMLExtractionService | None = None,
        markdown_converter: MarkdownConversionService | None = None,
        timeout: int = 30,
        max_size: int = 5 * 1024 * 1024,
    ) -> None:
        self.html_extractor = html_extractor or HTMLExtractionService(
            timeout=timeout,
            max_size=max_size,
        )
        self.markdown_converter = markdown_converter or MarkdownConversionService()

    async def fetch_as_markdown(self, url: str) -> str:
        """Fetch URL and return clean Markdown content.

        Args:
            url: The URL to fetch

        Returns:
            Clean Markdown representation of the page content

        Raises:
            HTTPException: If URL is invalid or fetch fails
        """
        logger.debug("Fetching URL as Markdown: %s", url)

        # Stage 1: Fetch and sanitize HTML (reuses security patterns)
        sanitized_html = await self.html_extractor.fetch_and_sanitize(url)

        if not sanitized_html:
            logger.warning("Empty content from URL: %s", url)
            return ""

        # Stage 2: Convert to Markdown
        markdown = self.markdown_converter.convert(sanitized_html)

        logger.debug(
            "Converted to Markdown: %d chars -> %d chars",
            len(sanitized_html),
            len(markdown),
        )

        return markdown
