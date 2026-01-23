"""Unit tests for _truncate_large_fields_for_sse helper function."""

from __future__ import annotations

from api.v1.chat import MAX_CONTENT_PREVIEW_CHARS, _truncate_large_fields_for_sse


def test_truncate_sse_with_none_input() -> None:
    """Test that None input returns None."""
    result = _truncate_large_fields_for_sse(None)
    assert result is None


def test_truncate_sse_long_content_is_truncated() -> None:
    """Test truncation of content strings longer than MAX_CONTENT_PREVIEW_CHARS."""
    long_content = "x" * (MAX_CONTENT_PREVIEW_CHARS + 100)
    tool_result = {"content": long_content}

    result = _truncate_large_fields_for_sse(tool_result)

    assert result is not None
    assert "content" in result
    assert isinstance(result["content"], str)
    assert len(result["content"]) == MAX_CONTENT_PREVIEW_CHARS + len(
        "... (truncated for display)"
    )
    assert result["content"].startswith("x" * MAX_CONTENT_PREVIEW_CHARS)
    assert result["content"].endswith("... (truncated for display)")


def test_truncate_sse_short_content_not_truncated() -> None:
    """Test that content strings <= MAX_CONTENT_PREVIEW_CHARS are not truncated."""
    short_content = "This is a short content string"
    tool_result = {"content": short_content}

    result = _truncate_large_fields_for_sse(tool_result)

    assert result is not None
    assert result["content"] == short_content


def test_truncate_sse_content_at_exact_limit_not_truncated() -> None:
    """Test that content exactly at MAX_CONTENT_PREVIEW_CHARS is not truncated."""
    exact_content = "x" * MAX_CONTENT_PREVIEW_CHARS
    tool_result = {"content": exact_content}

    result = _truncate_large_fields_for_sse(tool_result)

    assert result is not None
    assert result["content"] == exact_content


def test_truncate_sse_recipes_list_replaced_with_count() -> None:
    """Test replacement of recipes list with count message."""
    tool_result = {
        "recipes": [
            {"id": 1, "name": "Recipe 1"},
            {"id": 2, "name": "Recipe 2"},
            {"id": 3, "name": "Recipe 3"},
        ],
        "total_results": 5,
    }

    result = _truncate_large_fields_for_sse(tool_result)

    assert result is not None
    assert result["recipes"] == "(5 recipes found)"


def test_truncate_sse_recipes_without_total_results_uses_list_length() -> None:
    """Test handling of recipes without total_results field."""
    tool_result = {
        "recipes": [
            {"id": 1, "name": "Recipe 1"},
            {"id": 2, "name": "Recipe 2"},
        ]
    }

    result = _truncate_large_fields_for_sse(tool_result)

    assert result is not None
    assert result["recipes"] == "(2 recipes found)"


def test_truncate_sse_recipes_non_list_handled() -> None:
    """Test handling of non-list recipes field."""
    tool_result = {"recipes": "not a list"}

    result = _truncate_large_fields_for_sse(tool_result)

    assert result is not None
    assert result["recipes"] == "(0 recipes found)"


def test_truncate_sse_recipes_empty_list() -> None:
    """Test handling of empty recipes list."""
    tool_result = {"recipes": []}

    result = _truncate_large_fields_for_sse(tool_result)

    assert result is not None
    assert result["recipes"] == "(0 recipes found)"


def test_truncate_sse_original_dict_not_modified() -> None:
    """Test that the original dict is not modified (shallow copy works)."""
    long_content = "x" * (MAX_CONTENT_PREVIEW_CHARS + 100)
    original_recipes = [{"id": 1, "name": "Recipe 1"}]
    tool_result = {
        "content": long_content,
        "recipes": original_recipes,
        "total_results": 3,
    }

    # Store original values for comparison
    original_content = tool_result["content"]
    original_recipes_ref = tool_result["recipes"]

    result = _truncate_large_fields_for_sse(tool_result)

    # Verify the original dict is unchanged
    assert tool_result["content"] == original_content
    assert tool_result["recipes"] is original_recipes_ref
    assert tool_result["total_results"] == 3

    # Verify the result is different
    assert result is not None
    assert result["content"] != original_content
    assert result["recipes"] != original_recipes_ref


def test_truncate_sse_both_content_and_recipes_present() -> None:
    """Test with both content and recipes fields present."""
    long_content = "y" * (MAX_CONTENT_PREVIEW_CHARS + 50)
    tool_result = {
        "content": long_content,
        "recipes": [{"id": 1}, {"id": 2}],
        "total_results": 10,
    }

    result = _truncate_large_fields_for_sse(tool_result)

    assert result is not None
    assert result["content"] == (
        "y" * MAX_CONTENT_PREVIEW_CHARS + "... (truncated for display)"
    )
    assert result["recipes"] == "(10 recipes found)"


def test_truncate_sse_non_string_content_unchanged() -> None:
    """Test that non-string content values are not modified."""
    tool_result = {"content": 12345}

    result = _truncate_large_fields_for_sse(tool_result)

    assert result is not None
    assert result["content"] == 12345


def test_truncate_sse_other_fields_preserved() -> None:
    """Test that other fields in the dict are preserved unchanged."""
    tool_result = {
        "content": "x" * (MAX_CONTENT_PREVIEW_CHARS + 100),
        "recipes": [{"id": 1}],
        "other_field": "preserved",
        "numeric_field": 42,
        "nested": {"key": "value"},
    }

    result = _truncate_large_fields_for_sse(tool_result)

    assert result is not None
    assert result["other_field"] == "preserved"
    assert result["numeric_field"] == 42
    assert result["nested"] == {"key": "value"}


def test_truncate_sse_empty_dict() -> None:
    """Test handling of empty dict."""
    tool_result: dict[str, object] = {}

    result = _truncate_large_fields_for_sse(tool_result)

    assert result is not None
    assert result == {}


def test_truncate_sse_total_results_non_int() -> None:
    """Test handling when total_results is not an int."""
    tool_result = {
        "recipes": [{"id": 1}, {"id": 2}, {"id": 3}],
        "total_results": "not an int",
    }

    result = _truncate_large_fields_for_sse(tool_result)

    assert result is not None
    # Should fall back to list length
    assert result["recipes"] == "(3 recipes found)"
