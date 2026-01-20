"""Markdown conversion service for agentic tools."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from markdownify import ATX, MarkdownConverter as BaseConverter


if TYPE_CHECKING:
    from bs4 import BeautifulSoup


class RecipeMarkdownConverter(BaseConverter):
    """Custom Markdown converter optimized for recipe content."""

    def __init__(self, **options: Any) -> None:
        options.setdefault("heading_style", ATX)  # Use # style headers
        options.setdefault("bullets", "-")  # Consistent bullet style
        options.setdefault("wrap", False)  # Let LLM handle wrapping
        options.setdefault("strip", ["nav", "footer", "aside"])
        super().__init__(**options)

    def convert_img(self, el: object, text: str, parent_tags: set[str]) -> str:  # noqa: ARG002
        """Keep images with alt text, skip decorative images."""
        alt = getattr(el, "get", lambda x, y: y)("alt", "")
        src = getattr(el, "get", lambda x, y: y)("src", "")
        if alt and src:
            return f"![{alt}]({src})\n\n"
        return ""


class MarkdownConversionService:
    """Service for converting sanitized HTML to clean Markdown."""

    MAX_MARKDOWN_LENGTH = 50_000  # ~50KB for LLM context limits

    def __init__(self, converter: BaseConverter | None = None) -> None:
        self.converter = converter or RecipeMarkdownConverter()

    def convert(self, html: str) -> str:
        """Convert HTML string to clean Markdown."""
        raw_markdown = self.converter.convert(html)
        return self._clean_markdown(raw_markdown)

    def convert_soup(self, soup: BeautifulSoup) -> str:
        """Convert BeautifulSoup object to clean Markdown."""
        raw_markdown = self.converter.convert_soup(soup)
        return self._clean_markdown(raw_markdown)

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

        # Truncate if too long
        if len(result) > self.MAX_MARKDOWN_LENGTH:
            result = result[: self.MAX_MARKDOWN_LENGTH]
            result += "\n\n[Content truncated...]"

        return result
