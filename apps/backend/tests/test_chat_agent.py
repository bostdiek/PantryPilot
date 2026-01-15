"""Tests for chat agent service."""

from __future__ import annotations

from pydantic_ai import models

from schemas.chat_content import AssistantMessage, TextBlock
from services.chat_agent import normalize_agent_output


# Block any real model requests in tests
models.ALLOW_MODEL_REQUESTS = False


def test_normalize_agent_output_assistant_message() -> None:
    """Test normalization when output is already an AssistantMessage."""
    original = AssistantMessage(
        blocks=[TextBlock(type="text", text="Hello from Nibble")]
    )

    result = normalize_agent_output(original)

    assert result is original
    assert len(result.blocks) == 1
    assert isinstance(result.blocks[0], TextBlock)
    assert result.blocks[0].text == "Hello from Nibble"


def test_normalize_agent_output_string() -> None:
    """Test normalization when output is a plain string."""
    result = normalize_agent_output("Simple text response")

    assert isinstance(result, AssistantMessage)
    assert len(result.blocks) == 1
    assert isinstance(result.blocks[0], TextBlock)
    assert result.blocks[0].text == "Simple text response"


def test_normalize_agent_output_unknown_type() -> None:
    """Test normalization with unexpected output type (fallback case)."""
    result = normalize_agent_output({"unexpected": "format"})

    assert isinstance(result, AssistantMessage)
    assert len(result.blocks) == 1
    assert isinstance(result.blocks[0], TextBlock)
    assert result.blocks[0].text == "Unable to parse agent response."
