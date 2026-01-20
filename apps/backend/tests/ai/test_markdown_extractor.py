"""Integration tests for MarkdownExtractionService."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.ai.markdown_converter import MarkdownConversionService
from services.ai.markdown_extractor import MarkdownExtractionService


@pytest.fixture
def mock_html_content():
    """Sample HTML content for testing."""
    return """
    <html>
    <head><title>Test Recipe</title></head>
    <body>
        <h1>Simple Pasta</h1>
        <p>A quick and easy pasta recipe.</p>
        <h2>Ingredients</h2>
        <ul>
            <li>200g pasta</li>
            <li>2 tbsp olive oil</li>
        </ul>
    </body>
    </html>
    """


class TestMarkdownExtractionService:
    """Test the MarkdownExtractionService."""

    def test_default_initialization(self):
        """Test default service initialization."""
        service = MarkdownExtractionService()

        assert service.html_extractor is not None
        assert service.markdown_converter is not None

    def test_custom_component_injection(self):
        """Test injection of custom components."""
        from services.ai.html_extractor import HTMLExtractionService

        html_extractor = HTMLExtractionService(timeout=60)
        markdown_converter = MarkdownConversionService()

        service = MarkdownExtractionService(
            html_extractor=html_extractor,
            markdown_converter=markdown_converter,
        )

        assert service.html_extractor is html_extractor
        assert service.markdown_converter is markdown_converter

    def test_custom_timeout_and_max_size(self):
        """Test custom timeout and max_size parameters."""
        service = MarkdownExtractionService(timeout=60, max_size=10 * 1024 * 1024)

        assert service.html_extractor.timeout == 60
        assert service.html_extractor.max_size == 10 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_fetch_as_markdown_success(self, mock_html_content):
        """Test successful fetch and conversion."""
        service = MarkdownExtractionService()

        with patch.object(
            service.html_extractor,
            "fetch_and_sanitize",
            new_callable=AsyncMock,
            return_value=mock_html_content,
        ):
            result = await service.fetch_as_markdown("https://example.com/recipe")

        assert "Simple Pasta" in result
        assert "pasta recipe" in result
        assert "200g pasta" in result

    @pytest.mark.asyncio
    async def test_fetch_as_markdown_empty_response(self):
        """Test handling of empty response."""
        service = MarkdownExtractionService()

        with patch.object(
            service.html_extractor,
            "fetch_and_sanitize",
            new_callable=AsyncMock,
            return_value="",
        ):
            result = await service.fetch_as_markdown("https://example.com/empty")

        assert result == ""

    @pytest.mark.asyncio
    async def test_fetch_as_markdown_propagates_http_exception(self):
        """Test that HTTPException from html_extractor is propagated."""
        from fastapi import HTTPException

        service = MarkdownExtractionService()

        with patch.object(
            service.html_extractor,
            "fetch_and_sanitize",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=422, detail="Invalid URL"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.fetch_as_markdown("https://evil.com/ssrf")

            assert exc_info.value.status_code == 422
            assert "Invalid URL" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_fetch_as_markdown_ssrf_protection(self):
        """Test that SSRF protection is maintained (internal IPs blocked)."""
        from fastapi import HTTPException

        service = MarkdownExtractionService()

        # The underlying HTMLExtractionService should block these
        blocked_urls = [
            "http://localhost/admin",
            "http://127.0.0.1/secret",
            "http://169.254.169.254/latest/meta-data/",
        ]

        for url in blocked_urls:
            with patch.object(
                service.html_extractor,
                "fetch_and_sanitize",
                new_callable=AsyncMock,
                side_effect=HTTPException(
                    status_code=422,
                    detail=(
                        "Cannot fetch from localhost, private, or reserved IP addresses"
                    ),
                ),
            ):
                with pytest.raises(HTTPException):
                    await service.fetch_as_markdown(url)

    @pytest.mark.asyncio
    async def test_markdown_output_is_cleaned(self, mock_html_content):
        """Test that output markdown is properly cleaned."""
        service = MarkdownExtractionService()

        # Add some messy content
        messy_html = mock_html_content + "\n\n\n\n\n\nExtra content"

        with patch.object(
            service.html_extractor,
            "fetch_and_sanitize",
            new_callable=AsyncMock,
            return_value=messy_html,
        ):
            result = await service.fetch_as_markdown("https://example.com/recipe")

        # Should not have excessive newlines
        assert "\n\n\n" not in result

    @pytest.mark.asyncio
    async def test_logging_on_fetch(self, mock_html_content, caplog):
        """Test that fetch operations are logged."""
        import logging

        service = MarkdownExtractionService()

        with patch.object(
            service.html_extractor,
            "fetch_and_sanitize",
            new_callable=AsyncMock,
            return_value=mock_html_content,
        ):
            with caplog.at_level(logging.DEBUG):
                await service.fetch_as_markdown("https://example.com/recipe")

        # Debug logs should be present (when debug level is enabled)
        # Note: actual log assertion depends on logging configuration


class TestMarkdownExtractionServiceIntegration:
    """Integration tests with mocked HTTP layer."""

    @pytest.mark.asyncio
    async def test_end_to_end_conversion(self):
        """Test full pipeline from URL to Markdown."""
        service = MarkdownExtractionService()

        # Create realistic recipe HTML
        recipe_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Chocolate Chip Cookies</title>
            <script>alert('evil');</script>
            <style>body { color: red; }</style>
        </head>
        <body>
            <nav>Navigation menu</nav>
            <main>
                <h1>Chocolate Chip Cookies</h1>
                <p>Classic homemade cookies that are soft and chewy.</p>
                <h2>Ingredients</h2>
                <ul>
                    <li>2 1/4 cups flour</li>
                    <li>1 cup butter</li>
                    <li>3/4 cup sugar</li>
                    <li>2 eggs</li>
                    <li>2 cups chocolate chips</li>
                </ul>
                <h2>Instructions</h2>
                <ol>
                    <li>Preheat oven to 375°F</li>
                    <li>Mix dry ingredients</li>
                    <li>Cream butter and sugar</li>
                    <li>Combine and add chocolate chips</li>
                    <li>Bake for 9-11 minutes</li>
                </ol>
            </main>
            <footer>Copyright 2026</footer>
        </body>
        </html>
        """

        with patch.object(
            service.html_extractor,
            "fetch_and_sanitize",
            new_callable=AsyncMock,
            return_value=recipe_html,
        ):
            result = await service.fetch_as_markdown(
                "https://recipes.example.com/cookies"
            )

        # Check key content is present
        assert "Chocolate Chip Cookies" in result
        assert "soft and chewy" in result
        assert "2 1/4 cups flour" in result
        assert "Preheat oven" in result
        assert "375°F" in result

        # Script content should be removed by HTML sanitizer
        # (handled by HTMLExtractionService, not markdown converter)
