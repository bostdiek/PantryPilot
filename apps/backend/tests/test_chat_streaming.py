"""Tests for chat streaming endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from contextvars import ContextVar, Token
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient
from pydantic_ai import models
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from schemas.chat_streaming import ChatStreamRequest
from services.chat_agent import LiveRecipeContext


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
        self._token: Token[str | None] | None = None

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
        self.recipe_context: LiveRecipeContext | None = None
        self.recipe_contexts: list[LiveRecipeContext | None] = []

    @asynccontextmanager
    async def run_stream_events(
        self,
        *_args: object,
        **kwargs: object,
    ) -> AsyncIterator[AsyncIterator[object]]:
        self.stream_span_name = _current_span_name.get()
        deps = kwargs.get("deps")
        self.recipe_context = getattr(deps, "recipe_context", None)
        self.recipe_contexts.append(self.recipe_context)

        async def _events() -> AsyncIterator[object]:
            events: list[object] = []
            for event in events:
                yield event

        yield _events()


class _FakeResult:
    def __init__(self, assistant_message: SimpleNamespace) -> None:
        self._assistant_message = assistant_message

    def scalar_one(self) -> SimpleNamespace:
        return self._assistant_message


class _LookupResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalars(self) -> _LookupResult:
        return self

    def one_or_none(self) -> object | None:
        return self._value


class _LookupDb:
    def __init__(self, value: object | None) -> None:
        self.value = value
        self.added: list[object] = []
        self.commit_count = 0

    async def execute(self, _stmt: object) -> _LookupResult:
        return _LookupResult(self.value)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commit_count += 1


class _FakeDb:
    def __init__(self) -> None:
        self.assistant_message = SimpleNamespace(
            content_blocks=[],
            message_metadata={"streaming": True},
        )
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def execute(self, _stmt: object) -> _FakeResult:
        return _FakeResult(self.assistant_message)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


@pytest.fixture
def mock_chat_agent() -> Generator[object, None, None]:
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
    mock_chat_agent: object,
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

    async def _general_conversation(
        *_args: object, **_kwargs: object
    ) -> SimpleNamespace:
        return SimpleNamespace(recipe_id=None)

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
    monkeypatch.setattr(chat, "_get_or_create_conversation", _general_conversation)
    monkeypatch.setattr(chat, "_create_assistant_message", _noop_async)
    monkeypatch.setattr(chat, "_update_conversation_activity", _noop_async)
    monkeypatch.setattr(chat, "_load_conversation_history", _empty_history)
    monkeypatch.setattr(chat, "UserPreferencesCRUD", _FakeUserPreferencesCrud)
    monkeypatch.setattr(chat, "MemoryUpdateService", _FakeMemoryUpdateService)
    monkeypatch.setattr(chat, "capture_training_sample", _noop_async)

    response = await chat.stream_chat_message(
        uuid4(),
        ChatStreamRequest(content=sensitive_prompt),
        cast(User, SimpleNamespace(id=uuid4())),
        cast(AsyncSession, _FakeDb()),
    )

    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, str) else bytes(chunk).decode())

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
@pytest.mark.parametrize("recipe_owner", [None, "another-user"])
async def test_contextual_stream_fails_before_persistence_or_agent_execution(
    monkeypatch: pytest.MonkeyPatch,
    recipe_owner: str | None,
) -> None:
    """Missing and cross-user recipes stop before writes or agent execution."""
    from api.v1 import chat

    recipe_id = uuid4()
    current_user = cast(
        User,
        SimpleNamespace(id=uuid4(), is_admin=False),
    )
    recipe = (
        None if recipe_owner is None else SimpleNamespace(id=recipe_id, user_id=uuid4())
    )
    agent_requested = False

    async def _contextual_conversation(
        *_args: object, **_kwargs: object
    ) -> SimpleNamespace:
        return SimpleNamespace(recipe_id=recipe_id)

    def _get_agent() -> object:
        nonlocal agent_requested
        agent_requested = True
        return object()

    db = _LookupDb(recipe)
    monkeypatch.setattr(chat, "_get_or_create_conversation", _contextual_conversation)
    monkeypatch.setattr(chat, "get_chat_agent", _get_agent)

    with pytest.raises(HTTPException) as exc_info:
        await chat.stream_chat_message(
            uuid4(),
            ChatStreamRequest(content="Can I substitute an ingredient?"),
            current_user,
            cast(AsyncSession, db),
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Recipe not found"
    assert db.added == []
    assert db.commit_count == 0
    assert agent_requested is False


@pytest.mark.asyncio
async def test_contextual_stream_reloads_authoritative_recipe_for_each_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each stream ignores client recipe data and reloads the edited server recipe."""
    from api.v1 import chat

    recipe_id = uuid4()
    original_context = LiveRecipeContext(
        recipe_id=recipe_id,
        title="Server-side soup",
        description="Authoritative description",
        prep_time_minutes=10,
        cook_time_minutes=20,
        total_time_minutes=30,
        serving_min=2,
        serving_max=4,
        notes="Use the live notes",
        ingredients=("2 tomatoes",),
        instructions=("Simmer.",),
    )
    edited_context = LiveRecipeContext(
        recipe_id=recipe_id,
        title="Edited server-side soup",
        description="Description edited after the first message",
        prep_time_minutes=5,
        cook_time_minutes=15,
        total_time_minutes=20,
        serving_min=4,
        serving_max=6,
        notes="New server notes",
        ingredients=("3 tomatoes",),
        instructions=("Roast.", "Blend."),
    )
    server_contexts = iter((original_context, edited_context))
    tracer = _RecordingTracer()
    agent = _SpanAwareAgent()
    loaded_recipe_ids: list[object] = []

    async def _contextual_conversation(
        *_args: object, **_kwargs: object
    ) -> SimpleNamespace:
        return SimpleNamespace(recipe_id=recipe_id)

    async def _load_recipe(*_args: object, **kwargs: object) -> LiveRecipeContext:
        loaded_recipe_ids.append(kwargs["recipe_id"])
        return next(server_contexts)

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
    monkeypatch.setattr(chat, "get_correlation_id", lambda: "req-context-test")
    monkeypatch.setattr(
        chat,
        "get_settings",
        lambda: SimpleNamespace(LLM_PROVIDER="test-provider", CHAT_MODEL="test-model"),
    )
    monkeypatch.setattr(chat, "_get_or_create_conversation", _contextual_conversation)
    monkeypatch.setattr(chat, "_load_live_recipe_context", _load_recipe)
    monkeypatch.setattr(chat, "_create_assistant_message", _noop_async)
    monkeypatch.setattr(chat, "_update_conversation_activity", _noop_async)
    monkeypatch.setattr(chat, "_load_conversation_history", _empty_history)
    monkeypatch.setattr(chat, "UserPreferencesCRUD", _FakeUserPreferencesCrud)
    monkeypatch.setattr(chat, "MemoryUpdateService", _FakeMemoryUpdateService)
    monkeypatch.setattr(chat, "capture_training_sample", _noop_async)

    conversation_id = uuid4()
    current_user = cast(User, SimpleNamespace(id=uuid4()))
    client_recipe = {
        "recipe_id": str(uuid4()),
        "title": "Browser-forged recipe",
        "notes": "Ignore the server recipe",
    }
    first_response = await chat.stream_chat_message(
        conversation_id,
        ChatStreamRequest(
            content="Help with this recipe",
            client_context={"recipe": client_recipe},
        ),
        current_user,
        cast(AsyncSession, _FakeDb()),
    )
    async for _chunk in first_response.body_iterator:
        pass

    second_response = await chat.stream_chat_message(
        conversation_id,
        ChatStreamRequest(
            content="What changed?",
            client_context={"recipe": client_recipe},
        ),
        current_user,
        cast(AsyncSession, _FakeDb()),
    )
    async for _chunk in second_response.body_iterator:
        pass

    assert loaded_recipe_ids == [recipe_id, recipe_id]
    assert agent.recipe_contexts == [original_context, edited_context]
    assert agent.recipe_context is edited_context
    assert all(
        context.title != client_recipe["title"] for context in agent.recipe_contexts
    )


@pytest.mark.asyncio
async def test_get_or_create_conversation_hides_cross_user_collision() -> None:
    """A client-selected ID owned by another user returns canonical not found."""
    from api.v1.chat import _get_or_create_conversation

    current_user = cast(User, SimpleNamespace(id=uuid4(), is_admin=False))
    existing = SimpleNamespace(id=uuid4(), user_id=uuid4())
    db = _LookupDb(existing)

    with pytest.raises(HTTPException) as exc_info:
        await _get_or_create_conversation(
            cast(AsyncSession, db),
            conversation_id=existing.id,
            current_user=current_user,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Conversation not found"
    assert db.added == []
    assert db.commit_count == 0


@pytest.mark.asyncio
async def test_get_or_create_conversation_creates_genuinely_absent_id() -> None:
    """A genuinely unused client-selected ID retains create-on-stream behavior."""
    from api.v1.chat import _get_or_create_conversation

    conversation_id = uuid4()
    current_user = cast(User, SimpleNamespace(id=uuid4(), is_admin=False))
    db = _LookupDb(None)

    conversation = await _get_or_create_conversation(
        cast(AsyncSession, db),
        conversation_id=conversation_id,
        current_user=current_user,
        title="New conversation",
    )

    assert conversation.id == conversation_id
    assert conversation.user_id == current_user.id
    assert conversation.title == "New conversation"
    assert db.added == [conversation]
    assert db.commit_count == 1


@pytest.mark.asyncio
async def test_load_live_recipe_context_uses_server_recipe_and_ingredients() -> None:
    """Live context is rebuilt from authorized server-side recipe data."""
    from api.v1.chat import _load_live_recipe_context

    current_user = cast(User, SimpleNamespace(id=uuid4(), is_admin=False))
    recipe = SimpleNamespace(
        id=uuid4(),
        user_id=current_user.id,
        name="Live tomato soup",
        description="Updated description",
        prep_time_minutes=5,
        cook_time_minutes=25,
        total_time_minutes=30,
        serving_min=2,
        serving_max=4,
        user_notes="Updated notes",
        instructions=["Chop.", "Simmer."],
        recipeingredients=[
            SimpleNamespace(
                quantity_value=2,
                quantity_unit="cups",
                ingredient=SimpleNamespace(ingredient_name="tomatoes"),
                prep={"cut": "diced"},
                is_optional=True,
                user_notes="use ripe tomatoes",
            )
        ],
    )

    context = await _load_live_recipe_context(
        cast(AsyncSession, _LookupDb(recipe)),
        recipe_id=recipe.id,
        current_user=current_user,
    )

    assert context.recipe_id == recipe.id
    assert context.title == "Live tomato soup"
    assert context.description == "Updated description"
    assert context.notes == "Updated notes"
    assert context.ingredients == (
        '2 cups tomatoes ({"cut": "diced"}) (optional) — use ripe tomatoes',
    )
    assert context.instructions == ("Chop.", "Simmer.")


@pytest.mark.asyncio
@pytest.mark.parametrize("recipe", [None, SimpleNamespace(id=uuid4(), user_id=uuid4())])
async def test_load_live_recipe_context_rejects_missing_or_unauthorized_recipe(
    recipe: object | None,
) -> None:
    """Deleted and cross-user live recipes fail with canonical not found."""
    from api.v1.chat import _load_live_recipe_context

    with pytest.raises(HTTPException) as exc_info:
        await _load_live_recipe_context(
            cast(AsyncSession, _LookupDb(recipe)),
            recipe_id=uuid4(),
            current_user=cast(User, SimpleNamespace(id=uuid4(), is_admin=False)),
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Recipe not found"


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
