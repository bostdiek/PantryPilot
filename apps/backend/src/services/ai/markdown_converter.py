"""Markdown conversion service for agentic tools."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from markdownify import ATX, MarkdownConverter as BaseConverter


if TYPE_CHECKING:
    from bs4 import BeautifulSoup


class RecipeMarkdownConverter(BaseConverter):
    """Custom Markdown converter optimized for recipe content."""

    MAX_MARKDOWN_LENGTH = 12_000  # ~12KB (~3K tokens) - allows complex recipes

    def __init__(self, **options: Any) -> None:
        options.setdefault("heading_style", ATX)  # Use # style headers
        options.setdefault("bullets", "-")  # Consistent bullet style
        options.setdefault("wrap", False)  # Let LLM handle wrapping
        options.setdefault("strip", ["nav", "footer", "aside"])
        super().__init__(**options)

    def convert(self, html: str, **options: Any) -> str:
        """Convert HTML to markdown with automatic cleaning and truncation."""
        raw_markdown = super().convert(html, **options)
        return self._clean_markdown(raw_markdown)

    def convert_img(self, el: object, text: str, parent_tags: set[str]) -> str:  # noqa: ARG002
        """Strip images entirely - LLMs can't see them anyway.

        Token optimization: images consume tokens without providing value to LLMs.
        Even images with alt text are stripped since the LLM cannot process
        visual content.
        """
        return ""

    def _clean_markdown(self, markdown: str) -> str:
        """Post-process Markdown for LLM consumption."""
        # Normalize line endings
        result = markdown.replace("\r\n", "\n")

        # Collapse multiple blank lines to max 2
        result = re.sub(r"\n{3,}", "\n\n", result)

        # Remove leading/trailing whitespace per line
        lines = [line.strip() for line in result.split("\n")]
        result = "\n".join(lines)

        # Trim
        result = result.strip()

        # Truncate if too long (account for truncation message length)
        truncation_msg = "\n\n[Content truncated...]"
        if len(result) > self.MAX_MARKDOWN_LENGTH:
            # Truncate to fit within MAX_MARKDOWN_LENGTH including the message
            truncate_at = self.MAX_MARKDOWN_LENGTH - len(truncation_msg)
            result = result[:truncate_at] + truncation_msg

        return result


class MarkdownConversionService:
    """Service for converting sanitized HTML to clean Markdown.

    Delegates to RecipeMarkdownConverter by default, which handles cleaning.
    Can be used with custom converters if needed.
    """

    MAX_MARKDOWN_LENGTH = 12_000  # Matches RecipeMarkdownConverter default

    def __init__(self, converter: BaseConverter | None = None) -> None:
        self.converter = converter or RecipeMarkdownConverter()

    def convert(self, html: str) -> str:
        """Convert HTML string to clean Markdown."""
        raw_markdown = self.converter.convert(html)
        # Always apply cleaning to ensure consistent output regardless of converter
        return self._clean_markdown(raw_markdown)

    def convert_soup(self, soup: BeautifulSoup) -> str:
        """Convert BeautifulSoup object to clean Markdown."""
        # For soup, we need to call parent class method which doesn't have cleaning
        # So we apply cleaning here
        raw_markdown = self.converter.convert_soup(soup)
        # Always apply cleaning to ensure consistent output regardless of converter
        return self._clean_markdown(raw_markdown)

    def _clean_markdown(self, markdown: str) -> str:
        """Post-process Markdown for LLM consumption.

        Kept for backwards compatibility and testing.
        Delegates to RecipeMarkdownConverter if available.
        """
        if isinstance(self.converter, RecipeMarkdownConverter):
            return self.converter._clean_markdown(markdown)

        # Fallback implementation for non-RecipeMarkdownConverter
        result = markdown.replace("\r\n", "\n")
        result = re.sub(r"\n{3,}", "\n\n", result)
        lines = [line.strip() for line in result.split("\n")]
        result = "\n".join(lines)
        result = result.strip()

        truncation_msg = "\n\n[Content truncated...]"
        if len(result) > self.MAX_MARKDOWN_LENGTH:
            truncate_at = self.MAX_MARKDOWN_LENGTH - len(truncation_msg)
            result = result[:truncate_at] + truncation_msg

        return result
