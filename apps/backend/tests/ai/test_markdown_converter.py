"""Unit tests for MarkdownConversionService."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from services.ai.markdown_converter import (
    MarkdownConversionService,
    RecipeMarkdownConverter,
)


class TestRecipeMarkdownConverter:
    """Test the custom Markdown converter."""

    def test_default_options(self):
        """Test that default options are set correctly."""
        converter = RecipeMarkdownConverter()
        # Just verify it initializes without error
        assert converter is not None

    def test_convert_img_with_alt_and_src(self):
        """Test image conversion with alt text and src."""
        converter = RecipeMarkdownConverter()

        # Create a mock element with get method
        class MockElement:
            def get(self, attr, default=None):
                attrs = {"alt": "Delicious Pasta", "src": "https://example.com/img.jpg"}
                return attrs.get(attr, default)

        result = converter.convert_img(MockElement(), "", set())
        assert result == "![Delicious Pasta](https://example.com/img.jpg)\n\n"

    def test_convert_img_without_alt(self):
        """Test image conversion without alt text returns empty string."""
        converter = RecipeMarkdownConverter()

        class MockElement:
            def get(self, attr, default=None):
                attrs = {"src": "https://example.com/img.jpg"}
                return attrs.get(attr, default)

        result = converter.convert_img(MockElement(), "", set())
        assert result == ""

    def test_convert_img_without_src(self):
        """Test image conversion without src returns empty string."""
        converter = RecipeMarkdownConverter()

        class MockElement:
            def get(self, attr, default=None):
                attrs = {"alt": "Some text"}
                return attrs.get(attr, default)

        result = converter.convert_img(MockElement(), "", set())
        assert result == ""


class TestMarkdownConversionService:
    """Test the MarkdownConversionService."""

    def test_convert_simple_html(self):
        """Test conversion of simple HTML."""
        service = MarkdownConversionService()
        html = "<h1>Recipe Title</h1><p>This is a description.</p>"
        result = service.convert(html)

        assert "Recipe Title" in result
        assert "This is a description" in result

    def test_convert_html_with_list(self):
        """Test conversion of HTML with lists."""
        service = MarkdownConversionService()
        html = """
        <h2>Ingredients</h2>
        <ul>
            <li>1 cup flour</li>
            <li>2 eggs</li>
        </ul>
        """
        result = service.convert(html)

        assert "Ingredients" in result
        assert "1 cup flour" in result
        assert "2 eggs" in result

    def test_convert_soup(self):
        """Test conversion from BeautifulSoup object."""
        service = MarkdownConversionService()
        html = "<h1>Recipe</h1><p>Description</p>"
        soup = BeautifulSoup(html, "html.parser")

        result = service.convert_soup(soup)

        assert "Recipe" in result
        assert "Description" in result

    def test_clean_markdown_removes_excessive_newlines(self):
        """Test that clean_markdown collapses excessive blank lines."""
        service = MarkdownConversionService()

        # Test directly the _clean_markdown method
        markdown = "Line 1\n\n\n\n\nLine 2"
        result = service._clean_markdown(markdown)

        # Should have at most 2 newlines
        assert "\n\n\n" not in result
        assert "Line 1" in result
        assert "Line 2" in result

    def test_clean_markdown_normalizes_line_endings(self):
        """Test that Windows line endings are normalized."""
        service = MarkdownConversionService()

        markdown = "Line 1\r\nLine 2\r\n"
        result = service._clean_markdown(markdown)

        assert "\r\n" not in result

    def test_clean_markdown_strips_lines(self):
        """Test that whitespace is stripped from lines."""
        service = MarkdownConversionService()

        markdown = "  Line 1  \n  Line 2  "
        result = service._clean_markdown(markdown)

        # Lines should be stripped
        assert result == "Line 1\nLine 2"

    def test_truncation_at_max_length(self):
        """Test that content is truncated at MAX_MARKDOWN_LENGTH."""
        service = MarkdownConversionService()
        # Create content larger than max
        large_content = "A" * (service.MAX_MARKDOWN_LENGTH + 1000)

        result = service._clean_markdown(large_content)

        assert len(result) <= service.MAX_MARKDOWN_LENGTH + len(
            "\n\n[Content truncated...]"
        )
        assert "[Content truncated...]" in result

    def test_content_under_max_length_not_truncated(self):
        """Test that content under max length is not truncated."""
        service = MarkdownConversionService()
        content = "A" * 1000  # Small content

        result = service._clean_markdown(content)

        assert "[Content truncated...]" not in result
        assert len(result) == 1000

    def test_convert_empty_html(self):
        """Test conversion of empty HTML."""
        service = MarkdownConversionService()
        result = service.convert("")

        assert result == ""

    def test_custom_converter_injection(self):
        """Test that a custom converter can be injected."""
        from markdownify import MarkdownConverter

        custom_converter = MarkdownConverter()
        service = MarkdownConversionService(converter=custom_converter)

        assert service.converter is custom_converter


@pytest.fixture
def mock_recipe_html():
    """Sample recipe HTML for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Recipe</title></head>
    <body>
        <h1>Chicken Parmesan</h1>
        <p>A delicious Italian classic.</p>
        <h2>Ingredients</h2>
        <ul>
            <li>2 chicken breasts</li>
            <li>1 cup breadcrumbs</li>
            <li>1 cup marinara sauce</li>
        </ul>
        <h2>Instructions</h2>
        <ol>
            <li>Bread the chicken</li>
            <li>Fry until golden</li>
            <li>Top with sauce and cheese</li>
        </ol>
    </body>
    </html>
    """


def test_full_recipe_conversion(mock_recipe_html):
    """Test full recipe HTML conversion."""
    service = MarkdownConversionService()
    result = service.convert(mock_recipe_html)

    assert "Chicken Parmesan" in result
    assert "delicious Italian classic" in result
    assert "chicken breasts" in result
    assert "Bread the chicken" in result
