"""Tests for chat streaming endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextvars import ContextVar
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from pydantic_ai import models
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.chat_streaming import ChatStreamRequest


# Block any real model requests in tests
models.ALLOW_MODEL_REQUESTS = False


_current_span_name: ContextVar[str | None] = ContextVar(
    "current_test_span_name",
    default=None,
)


class _RecordingSpan:
    def __init__(self, name: str) -> None:
        self.name = name
        self.attributes: dict[str, object] = {}
        self.events: list[tuple[str, dict[str, object] | None]] = []
        self.exceptions: list[BaseException] = []
        self._token: object | None = None

    def __enter__(self) -> _RecordingSpan:
        self._token = _current_span_name.set(self.name)
        return self

    def __exit__(self, *args: object) -> None:
        if self._token is not None:
            _current_span_name.reset(self._token)

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def add_event(
        self,
        name: str,
        attributes: dict[str, object] | None = None,
    ) -> None:
        self.events.append((name, attributes))

    def record_exception(self, exception: BaseException) -> None:
        self.exceptions.append(exception)


class _RecordingTracer:
    def __init__(self) -> None:
        self.spans: list[_RecordingSpan] = []

    def start_as_current_span(self, name: str, **_kwargs: object) -> _RecordingSpan:
        span = _RecordingSpan(name)
        self.spans.append(span)
        return span


class _SpanAwareAgent:
    def __init__(self) -> None:
        self.stream_span_name: str | None = None

    async def run_stream_events(
        self,
        *_args: object,
        **_kwargs: object,
    ) -> AsyncIterator[object]:
        self.stream_span_name = _current_span_name.get()
        if False:
            yield object()


class _FakeResult:
    def __init__(self, assistant_message: SimpleNamespace) -> None:
        self._assistant_message = assistant_message

    def scalar_one(self) -> SimpleNamespace:
        return self._assistant_message


class _FakeDb:
    def __init__(self) -> None:
        self.assistant_message = SimpleNamespace(
            content_blocks=[],
            message_metadata={"streaming": True},
        )

    def add(self, _obj: object) -> None:
        return None

    async def execute(self, _stmt: object) -> _FakeResult:
        return _FakeResult(self.assistant_message)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


@pytest.fixture
def mock_chat_agent():
    """Mock the chat agent to avoid API key requirements."""
    from pydantic_ai import Agent

    from schemas.chat_content import AssistantMessage

    test_agent = Agent(
        TestModel(),
        output_type=AssistantMessage,
        name="Nibble",
    )

    with patch("services.chat_agent.get_chat_agent", return_value=test_agent):
        with patch("api.v1.chat.get_chat_agent", return_value=test_agent):
            yield test_agent


@pytest.mark.asyncio
async def test_stream_chat_message_success(
    async_client: AsyncClient,
    mock_chat_agent,
) -> None:
    """Test successful chat message streaming with SSE events."""
    conversation_id = uuid4()

    response = await async_client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages/stream",
        json={"content": "Hello Nibble, who are you?"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Parse SSE events from response
    events = []
    for line in response.text.strip().split("\n\n"):
        if line.startswith("data: "):
            events.append(line[6:])

    # Should have at least status, delta, and complete events
    assert len(events) >= 3


@pytest.mark.asyncio
async def test_agent_stream_runs_inside_assistant_span(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Pydantic AI streaming starts while assistant_message is current."""
    from api.v1 import chat

    sensitive_prompt = "secret family recipe prompt should not become span metadata"
    tracer = _RecordingTracer()
    agent = _SpanAwareAgent()

    async def _noop_async(*_args: object, **_kwargs: object) -> None:
        return None

    async def _empty_history(*_args: object, **_kwargs: object) -> list[object]:
        return []

    class _FakeUserPreferencesCrud:
        async def get_by_user_id(self, *_args: object, **_kwargs: object) -> None:
            return None

    class _FakeMemoryUpdateService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def get_memory_document(self, *_args: object, **_kwargs: object) -> None:
            return None

    monkeypatch.setattr(chat, "_tracer", tracer)
    monkeypatch.setattr(chat, "get_chat_agent", lambda: agent)
    monkeypatch.setattr(chat, "get_correlation_id", lambda: "req-span-test")
    monkeypatch.setattr(
        chat,
        "get_settings",
        lambda: SimpleNamespace(LLM_PROVIDER="test-provider", CHAT_MODEL="test-model"),
    )
    monkeypatch.setattr(chat, "_get_or_create_conversation", _noop_async)
    monkeypatch.setattr(chat, "_create_assistant_message", _noop_async)
    monkeypatch.setattr(chat, "_update_conversation_activity", _noop_async)
    monkeypatch.setattr(chat, "_load_conversation_history", _empty_history)
    monkeypatch.setattr(chat, "UserPreferencesCRUD", _FakeUserPreferencesCrud)
    monkeypatch.setattr(chat, "MemoryUpdateService", _FakeMemoryUpdateService)
    monkeypatch.setattr(chat, "capture_training_sample", _noop_async)

    response = await chat.stream_chat_message(
        uuid4(),
        ChatStreamRequest(content=sensitive_prompt),
        SimpleNamespace(id=uuid4()),
        cast(AsyncSession, _FakeDb()),
    )

    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)

    assert agent.stream_span_name == "assistant_message"
    assert any('"event":"message.complete"' in chunk for chunk in chunks)
    assistant_spans = [
        span for span in tracer.spans if span.name == "assistant_message"
    ]
    assert len(assistant_spans) == 1
    assistant_span = assistant_spans[0]
    assert assistant_span.attributes["product.telemetry.request_id"] == "req-span-test"
    assert sensitive_prompt not in str(assistant_span.attributes)
    assert all(sensitive_prompt not in str(event) for event in assistant_span.events)


@pytest.mark.asyncio
async def test_stream_chat_message_invalid_payload(
    async_client: AsyncClient,
) -> None:
    """Test that invalid payloads are rejected."""
    conversation_id = uuid4()

    response = await async_client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages/stream",
        json={},  # Missing required 'content' field
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
