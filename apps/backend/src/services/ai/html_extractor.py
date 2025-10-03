"""HTML extraction and sanitization service."""

import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Comment
from fastapi import HTTPException, status


logger = logging.getLogger(__name__)


class HTMLExtractionService:
    """Service for fetching and sanitizing HTML content from recipe URLs."""

    # Common recipe content selectors (ordered by specificity)
    RECIPE_SELECTORS = [
        '[itemtype*="Recipe"]',  # JSON-LD Recipe schema
        ".recipe",
        ".recipe-card",
        ".recipe-content",
        ".entry-content",
        "article",
        "main",
    ]

    # Tags to remove completely
    UNWANTED_TAGS = {
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        "iframe",
        "embed",
        "object",
        "applet",
        "form",
        "input",
        "button",
        "select",
        "textarea",
        "noscript",
        "meta",
        "link",
    }

    # Attributes to remove (for security and cleanup)
    UNWANTED_ATTRS = {
        "onclick",
        "onload",
        "onerror",
        "onmouseover",
        "onmouseout",
        "onfocus",
        "onblur",
        "onchange",
        "onsubmit",
        "onreset",
        "style",
        "class",
        "id",
        "data-*",
    }

    def __init__(self, timeout: int = 30, max_size: int = 5 * 1024 * 1024):
        """Initialize the HTML extraction service.

        Args:
            timeout: Request timeout in seconds
            max_size: Maximum response size in bytes (5MB default)
        """
        self.timeout = timeout
        self.max_size = max_size

    async def fetch_and_sanitize(self, url: str) -> str:
        """Fetch HTML from URL and return sanitized content.

        Args:
            url: The URL to fetch

        Returns:
            Clean, sanitized HTML content

        Raises:
            HTTPException: If URL is invalid or fetch fails
        """
        # Validate URL
        self._validate_url(url)

        # Fetch HTML content
        html_content = await self._fetch_html(url)

        # Parse and sanitize
        sanitized_content = self._sanitize_html(html_content, url)

        return sanitized_content

    def _validate_url(self, url: str) -> None:
        """Validate that the URL is safe to fetch.

        Args:
            url: URL to validate

        Raises:
            HTTPException: If URL is invalid or unsafe
        """
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid URL format: {str(e)}",
            ) from e

        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="URL must include scheme and domain",
            )

        if parsed.scheme not in ("http", "https"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="URL must use HTTP or HTTPS protocol",
            )

        # Block localhost and private IPs for security
        if parsed.hostname in ("localhost", "127.0.0.1") or (
            parsed.hostname
            and (
                parsed.hostname.startswith("192.168.")
                or parsed.hostname.startswith("10.")
                or parsed.hostname.startswith("172.")
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot fetch from localhost or private IP addresses",
            )

    async def _fetch_html(self, url: str) -> str:
        """Fetch HTML content from the URL.

        Args:
            url: URL to fetch

        Returns:
            Raw HTML content

        Raises:
            HTTPException: If fetch fails
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; PantryPilot-RecipeBot/1.0; "
                "+https://github.com/bostdiek/PantryPilot)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            ) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                # Check content length
                if len(response.content) > self.max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Response too large: {len(response.content)} bytes",
                    )

                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                if "html" not in content_type:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Expected HTML content, got: {content_type}",
                    )

                return response.text

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Failed to fetch URL: {e.response.status_code} "
                    f"{e.response.reason_phrase}"
                ),
            ) from e
        except httpx.TimeoutException as e:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT, detail="Request timed out"
            ) from e
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Network error: {str(e)}",
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch content",
            ) from e

    def _sanitize_html(self, html: str, base_url: str) -> str:
        """Sanitize HTML content and extract recipe-relevant sections.

        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            Sanitized HTML focused on recipe content
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            logger.warning(f"Failed to parse HTML: {e}")
            return ""

        # Remove unwanted elements completely
        for tag_name in self.UNWANTED_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Try to find recipe-specific content
        recipe_content = self._extract_recipe_content(soup)

        if recipe_content:
            soup = recipe_content

        # Clean up remaining tags and attributes
        self._clean_attributes(soup)

        # Clean up text content
        self._clean_text_content(soup)

        # Convert relative URLs to absolute
        self._resolve_urls(soup, base_url)

        return str(soup)

    def _extract_recipe_content(self, soup: BeautifulSoup) -> BeautifulSoup | None:
        """Try to extract recipe-specific content from the page.

        Args:
            soup: BeautifulSoup object

        Returns:
            BeautifulSoup object with recipe content, or None
        """
        for selector in self.RECIPE_SELECTORS:
            elements = soup.select(selector)
            if elements:
                # Return the first matching element
                recipe_soup = BeautifulSoup("", "html.parser")
                recipe_soup.append(elements[0])
                return recipe_soup

        return None

    def _clean_attributes(self, soup: BeautifulSoup) -> None:
        """Remove unwanted attributes from all tags.

        Args:
            soup: BeautifulSoup object to clean
        """
        for tag in soup.find_all():
            # Keep only safe attributes
            attrs_to_keep = {}
            for attr, value in tag.attrs.items():
                # Keep href for links, src for images, alt for images
                if attr.lower() in ("href", "src", "alt", "title"):
                    attrs_to_keep[attr] = value

            tag.attrs.clear()
            tag.attrs.update(attrs_to_keep)

    def _clean_text_content(self, soup: BeautifulSoup) -> None:
        """Clean up text content within the HTML.

        Args:
            soup: BeautifulSoup object to clean
        """
        # Remove excessive whitespace
        for element in soup.descendants:
            if hasattr(element, "string") and element.string:
                cleaned = re.sub(r"\s+", " ", element.string).strip()
                if cleaned != element.string:
                    element.string.replace_with(cleaned)

    def _resolve_urls(self, soup: BeautifulSoup, base_url: str) -> None:
        """Convert relative URLs to absolute URLs.

        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolution
        """
        # Resolve href attributes
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if isinstance(href, str):
                link["href"] = urljoin(base_url, href)

        # Resolve src attributes (images, etc.)
        for element in soup.find_all(src=True):
            src = element["src"]
            if isinstance(src, str):
                element["src"] = urljoin(base_url, src)
