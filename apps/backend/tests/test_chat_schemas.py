"""Tests for chat streaming schemas."""

from __future__ import annotations

from uuid import uuid4

import pytest

from schemas.chat_streaming import (
    MAX_SSE_EVENT_BYTES,
    ChatSseEvent,
    ChatStreamRequest,
    ConversationSummary,
    RecipeConversationContext,
)


def test_chat_stream_request_validation() -> None:
    """Test that ChatStreamRequest validates content properly."""
    request = ChatStreamRequest(content="Hello Nibble!")
    assert request.content == "Hello Nibble!"


def test_conversation_summary_recipe_context_contract() -> None:
    """Conversation summaries distinguish contextual and general threads."""
    recipe_id = uuid4()
    contextual = ConversationSummary(
        id=uuid4(),
        title="Recipe chat",
        created_at="2026-09-28T12:00:00+00:00",
        last_activity_at="2026-09-28T12:00:00+00:00",
        recipe_context=RecipeConversationContext(
            recipe_id=recipe_id,
            recipe_title="Tomato Soup",
            is_current=True,
        ),
    )
    general = ConversationSummary(
        id=uuid4(),
        title="General chat",
        created_at="2026-09-28T12:00:00+00:00",
        last_activity_at="2026-09-28T12:00:00+00:00",
    )

    assert contextual.model_dump(mode="json")["recipe_context"] == {
        "recipe_id": str(recipe_id),
        "recipe_title": "Tomato Soup",
        "is_current": True,
    }
    assert general.model_dump(mode="json")["recipe_context"] is None


def test_chat_sse_event_creation() -> None:
    """Test ChatSseEvent can be created with required fields."""
    conversation_id = uuid4()
    message_id = uuid4()

    event = ChatSseEvent(
        event="message.delta",
        conversation_id=conversation_id,
        message_id=message_id,
        data={"delta": "Hello"},
    )

    assert event.event == "message.delta"
    assert event.conversation_id == conversation_id
    assert event.message_id == message_id
    assert event.data == {"delta": "Hello"}


def test_chat_sse_event_to_sse_format() -> None:
    """Test that to_sse() produces valid SSE format."""
    conversation_id = uuid4()
    message_id = uuid4()

    event = ChatSseEvent(
        event="status",
        conversation_id=conversation_id,
        message_id=message_id,
        data={"status": "thinking"},
    )

    sse_output = event.to_sse()

    # SSE format should start with "data: "
    assert sse_output.startswith("data: ")
    # Should end with double newline
    assert sse_output.endswith("\n\n")
    # Should contain the event data
    assert '"event":"status"' in sse_output
    assert '"status":"thinking"' in sse_output


def test_chat_sse_event_size_constraint() -> None:
    """Test that to_sse() enforces payload size limits."""
    conversation_id = uuid4()
    message_id = uuid4()

    # Create event with data that will exceed MAX_SSE_EVENT_BYTES
    large_text = "x" * MAX_SSE_EVENT_BYTES
    event = ChatSseEvent(
        event="message.delta",
        conversation_id=conversation_id,
        message_id=message_id,
        data={"delta": large_text},
    )

    with pytest.raises(ValueError, match="SSE payload exceeded MAX_SSE_EVENT_BYTES"):
        event.to_sse()


def test_chat_sse_event_small_payload_ok() -> None:
    """Test that reasonable-sized payloads serialize successfully."""
    conversation_id = uuid4()
    message_id = uuid4()

    event = ChatSseEvent(
        event="blocks.append",
        conversation_id=conversation_id,
        message_id=message_id,
        data={
            "block": {
                "type": "text",
                "text": "This is a normal-sized response from Nibble.",
            }
        },
    )

    # Should not raise
    sse_output = event.to_sse()
    assert len(sse_output) > 0
    assert sse_output.startswith("data: ")


def test_chat_sse_event_tool_started_serializes() -> None:
    conversation_id = uuid4()
    message_id = uuid4()

    event = ChatSseEvent(
        event="tool.started",
        conversation_id=conversation_id,
        message_id=message_id,
        data={
            "tool_call_id": "call_123",
            "tool_name": "get_daily_weather",
            "arguments": {"zip": "12345"},
        },
    )

    sse_output = event.to_sse()
    assert '"event":"tool.started"' in sse_output
    assert '"tool_call_id":"call_123"' in sse_output
