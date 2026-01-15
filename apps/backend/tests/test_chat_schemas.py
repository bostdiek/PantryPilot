"""Tests for chat streaming schemas."""

from __future__ import annotations

from uuid import uuid4

import pytest

from schemas.chat_streaming import MAX_SSE_EVENT_BYTES, ChatSseEvent, ChatStreamRequest


def test_chat_stream_request_validation() -> None:
    """Test that ChatStreamRequest validates content properly."""
    request = ChatStreamRequest(content="Hello Nibble!")
    assert request.content == "Hello Nibble!"


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
