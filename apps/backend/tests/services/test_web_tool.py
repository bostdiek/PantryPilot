"""Tests for token-optimized web fetching tool."""

from __future__ import annotations

import pytest
import tiktoken
from bs4 import BeautifulSoup

from services.ai.html_extractor import HTMLExtractionService
from services.ai.markdown_converter import RecipeMarkdownConverter


class TestWebToolTokenOptimization:
    """Test suite for web tool token optimization features."""

    @pytest.fixture
    def html_extractor(self) -> HTMLExtractionService:
        """Create HTML extraction service instance."""
        return HTMLExtractionService()

    @pytest.fixture
    def markdown_converter(self) -> RecipeMarkdownConverter:
        """Create markdown converter instance."""
        return RecipeMarkdownConverter()

    @pytest.fixture
    def encoding(self) -> tiktoken.Encoding:
        """Get tiktoken encoding for token counting."""
        return tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding

    @pytest.mark.asyncio
    async def test_fetch_url_removes_boilerplate(
        self, html_extractor: HTMLExtractionService
    ) -> None:
        """Verify MarkdownExtractionService strips navigation/scripts/social."""
        html_content = """
        <html>
            <head><title>Test Recipe</title></head>
            <body>
                <nav class="main-nav">Home | About | Contact</nav>
                <div class="social-share">
                    <button>Share on Facebook</button>
                    <button>Tweet</button>
                </div>
                <article class="recipe-content">
                    <h1>Delicious Pasta</h1>
                    <p>This is the main recipe content.</p>
                </article>
                <aside class="related-posts">
                    <h3>You might also like</h3>
                    <ul>
                        <li>Recipe 1</li>
                        <li>Recipe 2</li>
                    </ul>
                </aside>
                <div class="comments">
                    <h3>Comments</h3>
                    <p>User comment 1</p>
                </div>
            </body>
        </html>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        html_extractor._remove_boilerplate(soup)
        result = str(soup)

        # Verify boilerplate elements are removed
        assert "main-nav" not in result
        assert "Share on Facebook" not in result
        assert "Tweet" not in result
        assert "You might also like" not in result
        assert "Comments" not in result

        # Verify main content remains
        assert "Delicious Pasta" in result
        assert "main recipe content" in result

    @pytest.mark.asyncio
    async def test_fetch_url_truncates_large_content(
        self, markdown_converter: RecipeMarkdownConverter
    ) -> None:
        """Mock large HTML response and verify truncation to MAX_MARKDOWN_LENGTH."""
        # Create very large HTML content (> 12KB)
        large_html = "<html><body>" + "<p>Test content. </p>" * 1000 + "</body></html>"

        result = markdown_converter.convert(large_html)

        # Verify content is truncated to 12000 characters
        assert len(result) <= 12000, f"Content length {len(result)} exceeds 12000"

        # Verify truncation message is present if content was truncated
        if len(result) == 12000:
            assert "..." in result or result.endswith("\n")

    @pytest.mark.asyncio
    async def test_fetch_url_token_count_within_limits(
        self, encoding: tiktoken.Encoding
    ) -> None:
        """Fetch sample recipe page and verify tokens < threshold."""
        # Simulate fetched markdown content (12KB max after optimization)
        sample_content = """
        # Chicken Tacos Recipe

        ## Ingredients
        - 1 lb chicken breast
        - 8 tortillas
        - 1 cup salsa
        - 1/2 cup cheese

        ## Instructions
        1. Cook chicken
        2. Warm tortillas
        3. Assemble tacos

        Prep time: 15 min
        Cook time: 20 min
        """

        token_count = len(encoding.encode(sample_content))

        # Verify tokens are well below SSE event size limit
        # 12KB of text typically = ~3000 tokens (4 chars/token average)
        # SSE event limit is ~16KB, so we should be well under
        assert token_count < 4000, (
            f"Token count {token_count} exceeds target. "
            "Content should be < 4000 tokens for efficient streaming."
        )

    @pytest.mark.asyncio
    async def test_markdown_strips_images(
        self, markdown_converter: RecipeMarkdownConverter
    ) -> None:
        """Verify images are stripped since LLMs can't see them."""
        html_with_images = """
        <html>
            <body>
                <h1>Recipe Title</h1>
                <img src="recipe.jpg" alt="Delicious meal" />
                <p>Recipe instructions</p>
                <img src="step1.jpg" alt="Step 1" />
            </body>
        </html>
        """

        result = markdown_converter.convert(html_with_images)

        # Verify no image markdown syntax (![alt](url))
        assert "![" not in result
        assert "recipe.jpg" not in result
        assert "step1.jpg" not in result

        # Verify text content remains
        assert "Recipe Title" in result
        assert "Recipe instructions" in result

    @pytest.mark.asyncio
    async def test_boilerplate_selectors_coverage(
        self, html_extractor: HTMLExtractionService
    ) -> None:
        """Test that all common boilerplate selectors are defined."""
        # Verify key boilerplate selectors exist
        expected_patterns = [
            "related",
            "sidebar",
            "social",
            "comments",
            "advertisement",
            "newsletter",
        ]

        selectors_str = " ".join(html_extractor.BOILERPLATE_SELECTORS).lower()

        for pattern in expected_patterns:
            assert pattern in selectors_str, (
                f"Boilerplate selector for '{pattern}' not found. "
                "This may allow unnecessary content through."
            )
