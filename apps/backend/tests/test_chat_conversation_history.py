"""Tests for chat conversation history endpoints (Phase 1 integration)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from api.v1.chat import (
    _convert_db_messages_to_pydantic_ai,
    _extract_text_from_blocks,
    _generate_conversation_title,
)
from dependencies.auth import get_current_user
from dependencies.db import get_db
from main import app


# -----------------------------------------------------------------------------
# Helper Classes for Mocking
# -----------------------------------------------------------------------------


class _MockChatMessage:
    """Mock ChatMessage for testing conversion functions."""

    def __init__(
        self,
        *,
        id: UUID | None = None,
        role: str = "user",
        content_blocks: list[dict[str, Any]] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.role = role
        self.content_blocks = content_blocks or []
        self.created_at = created_at or datetime.now(UTC)


class _MockConversation:
    """Mock ChatConversation for testing."""

    def __init__(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID | None = None,
        title: str | None = None,
        created_at: datetime | None = None,
        last_activity_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.user_id = user_id or uuid4()
        self.title = title
        self.created_at = created_at or datetime.now(UTC)
        self.last_activity_at = last_activity_at or datetime.now(UTC)


class _ScalarsResult:
    """Mock for SQLAlchemy scalars() result."""

    def __init__(self, items: list[Any] | None = None, single: Any | None = None):
        self._items = items or []
        self._single = single

    def all(self) -> list[Any]:
        return self._items

    def one_or_none(self) -> Any | None:
        return self._single


class _ExecuteResult:
    """Mock for SQLAlchemy execute() result."""

    def __init__(self, items: list[Any] | None = None, single: Any | None = None):
        self._items = items or []
        self._single = single
        self._scalar_value: int | None = None

    def scalars(self) -> _ScalarsResult:
        return _ScalarsResult(items=self._items, single=self._single)

    def scalar(self) -> int | None:
        return self._scalar_value


class _FakeDbSession:
    """Fake async DB session for testing."""

    def __init__(
        self,
        *,
        conversations: list[_MockConversation] | None = None,
        messages: list[_MockChatMessage] | None = None,
        conversation: _MockConversation | None = None,
        total_count: int = 0,
    ) -> None:
        self._conversations = conversations or []
        self._messages = messages or []
        self._conversation = conversation
        self._total_count = total_count
        self.added: list[Any] = []
        self.commits: int = 0
        self._call_count = 0

    async def execute(self, stmt: Any) -> _ExecuteResult:
        self._call_count += 1
        # First call is usually count query
        if self._call_count == 1 and self._total_count > 0:
            result = _ExecuteResult()
            result._scalar_value = self._total_count
            return result
        # Return conversations or messages based on what's set
        if self._conversations:
            return _ExecuteResult(items=self._conversations)
        if self._messages:
            return _ExecuteResult(items=self._messages)
        if self._conversation:
            return _ExecuteResult(single=self._conversation)
        return _ExecuteResult()

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1


# -----------------------------------------------------------------------------
# Unit Tests for Helper Functions
# -----------------------------------------------------------------------------


class TestExtractTextFromBlocks:
    """Tests for _extract_text_from_blocks helper."""

    def test_extract_single_text_block(self) -> None:
        blocks = [{"type": "text", "text": "Hello world"}]
        result = _extract_text_from_blocks(blocks)
        assert result == "Hello world"

    def test_extract_multiple_text_blocks(self) -> None:
        blocks = [
            {"type": "text", "text": "First line"},
            {"type": "text", "text": "Second line"},
        ]
        result = _extract_text_from_blocks(blocks)
        assert result == "First line\nSecond line"

    def test_ignore_non_text_blocks(self) -> None:
        blocks = [
            {"type": "text", "text": "Hello"},
            {"type": "link", "url": "https://example.com"},
            {"type": "text", "text": "World"},
        ]
        result = _extract_text_from_blocks(blocks)
        assert result == "Hello\nWorld"

    def test_empty_blocks(self) -> None:
        blocks: list[dict[str, Any]] = []
        result = _extract_text_from_blocks(blocks)
        assert result == ""

    def test_blocks_with_empty_text(self) -> None:
        blocks = [
            {"type": "text", "text": ""},
            {"type": "text", "text": "Valid"},
        ]
        result = _extract_text_from_blocks(blocks)
        assert result == "Valid"


class TestConvertDbMessagesToPydanticAi:
    """Tests for _convert_db_messages_to_pydantic_ai helper."""

    def test_convert_user_message(self) -> None:
        messages = [
            _MockChatMessage(
                role="user",
                content_blocks=[{"type": "text", "text": "Hello"}],
            )
        ]
        result = _convert_db_messages_to_pydantic_ai(messages)  # type: ignore[arg-type]
        assert len(result) == 1
        # ModelRequest for user messages
        assert hasattr(result[0], "parts")

    def test_convert_assistant_message(self) -> None:
        messages = [
            _MockChatMessage(
                role="assistant",
                content_blocks=[{"type": "text", "text": "Hi there!"}],
            )
        ]
        result = _convert_db_messages_to_pydantic_ai(messages)  # type: ignore[arg-type]
        assert len(result) == 1
        # ModelResponse for assistant messages
        assert hasattr(result[0], "parts")

    def test_convert_mixed_conversation(self) -> None:
        messages = [
            _MockChatMessage(
                role="user",
                content_blocks=[{"type": "text", "text": "Question?"}],
            ),
            _MockChatMessage(
                role="assistant",
                content_blocks=[{"type": "text", "text": "Answer!"}],
            ),
            _MockChatMessage(
                role="user",
                content_blocks=[{"type": "text", "text": "Follow up"}],
            ),
        ]
        result = _convert_db_messages_to_pydantic_ai(messages)  # type: ignore[arg-type]
        assert len(result) == 3

    def test_skip_empty_content_messages(self) -> None:
        messages = [
            _MockChatMessage(
                role="user",
                content_blocks=[{"type": "text", "text": "Hello"}],
            ),
            _MockChatMessage(
                role="assistant",
                content_blocks=[],  # Empty
            ),
            _MockChatMessage(
                role="user",
                content_blocks=[{"type": "text", "text": "Still here"}],
            ),
        ]
        result = _convert_db_messages_to_pydantic_ai(messages)  # type: ignore[arg-type]
        assert len(result) == 2

    def test_skip_system_and_tool_roles(self) -> None:
        messages = [
            _MockChatMessage(
                role="system",
                content_blocks=[{"type": "text", "text": "System prompt"}],
            ),
            _MockChatMessage(
                role="tool",
                content_blocks=[{"type": "text", "text": "Tool result"}],
            ),
            _MockChatMessage(
                role="user",
                content_blocks=[{"type": "text", "text": "User message"}],
            ),
        ]
        result = _convert_db_messages_to_pydantic_ai(messages)  # type: ignore[arg-type]
        assert len(result) == 1


class TestGenerateConversationTitle:
    """Tests for _generate_conversation_title helper."""

    def test_generates_title_with_date_and_time(self) -> None:
        title = _generate_conversation_title()
        assert title.startswith("Chat started ")
        # Should contain date format like "Jan 17, 2026"
        assert "at" in title


# -----------------------------------------------------------------------------
# Integration Tests for Endpoints
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_conversations_empty() -> None:
    """Test listing conversations when user has none."""
    user_id = uuid4()
    db = _FakeDbSession(conversations=[], total_count=0)

    async def _override_get_db():
        yield db

    async def _override_current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_current_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get("/api/v1/chat/conversations")

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["conversations"] == []
        assert body["total"] == 0
        assert body["has_more"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_conversations_with_data() -> None:
    """Test listing conversations with existing data."""
    user_id = uuid4()
    conv1 = _MockConversation(user_id=user_id, title="First chat")
    conv2 = _MockConversation(user_id=user_id, title="Second chat")

    # Custom db session that returns count first, then conversations
    class _ConvListDbSession:
        def __init__(self):
            self._call_count = 0

        async def execute(self, stmt):
            self._call_count += 1
            if self._call_count == 1:
                # Count query
                result = _ExecuteResult()
                result._scalar_value = 2
                return result
            # Conversations query
            return _ExecuteResult(items=[conv1, conv2])

    db = _ConvListDbSession()

    async def _override_get_db():
        yield db

    async def _override_current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_current_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get("/api/v1/chat/conversations")

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert len(body["conversations"]) == 2
        assert body["total"] == 2
        assert body["has_more"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_conversations_pagination() -> None:
    """Test pagination parameters for conversation list."""
    user_id = uuid4()

    class _PaginatedDbSession:
        def __init__(self):
            self._call_count = 0

        async def execute(self, stmt):
            self._call_count += 1
            if self._call_count == 1:
                result = _ExecuteResult()
                result._scalar_value = 50  # 50 total conversations
                return result
            # Return 20 conversations (default limit)
            convs = [_MockConversation(user_id=user_id) for _ in range(20)]
            return _ExecuteResult(items=convs)

    db = _PaginatedDbSession()

    async def _override_get_db():
        yield db

    async def _override_current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_current_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(
                "/api/v1/chat/conversations", params={"limit": 20, "offset": 0}
            )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert len(body["conversations"]) == 20
        assert body["total"] == 50
        assert body["has_more"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_message_history_conversation_not_found() -> None:
    """Test message history returns 404 for non-existent conversation."""
    user_id = uuid4()
    conversation_id = uuid4()

    class _NotFoundDbSession:
        async def execute(self, stmt):
            return _ExecuteResult(single=None)  # No conversation found

    db = _NotFoundDbSession()

    async def _override_get_db():
        yield db

    async def _override_current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_current_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(
                f"/api/v1/chat/conversations/{conversation_id}/messages"
            )

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        body = resp.json()
        assert "not found" in body["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_message_history_empty() -> None:
    """Test message history for conversation with no messages."""
    user_id = uuid4()
    conversation_id = uuid4()
    conv = _MockConversation(id=conversation_id, user_id=user_id)

    class _EmptyMessagesDbSession:
        def __init__(self):
            self._call_count = 0

        async def execute(self, stmt):
            self._call_count += 1
            if self._call_count == 1:
                # Conversation lookup
                return _ExecuteResult(single=conv)
            # Messages query - empty
            return _ExecuteResult(items=[])

    db = _EmptyMessagesDbSession()

    async def _override_get_db():
        yield db

    async def _override_current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_current_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(
                f"/api/v1/chat/conversations/{conversation_id}/messages"
            )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["messages"] == []
        assert body["has_more"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_message_history_with_messages() -> None:
    """Test message history returns messages correctly."""
    user_id = uuid4()
    conversation_id = uuid4()
    conv = _MockConversation(id=conversation_id, user_id=user_id)

    msg1 = _MockChatMessage(
        role="user",
        content_blocks=[{"type": "text", "text": "Hello"}],
        created_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    msg2 = _MockChatMessage(
        role="assistant",
        content_blocks=[{"type": "text", "text": "Hi there!"}],
        created_at=datetime.now(UTC) - timedelta(minutes=4),
    )

    class _MessagesDbSession:
        def __init__(self):
            self._call_count = 0

        async def execute(self, stmt):
            self._call_count += 1
            if self._call_count == 1:
                return _ExecuteResult(single=conv)
            return _ExecuteResult(items=[msg1, msg2])

    db = _MessagesDbSession()

    async def _override_get_db():
        yield db

    async def _override_current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_current_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(
                f"/api/v1/chat/conversations/{conversation_id}/messages"
            )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][1]["role"] == "assistant"
        assert body["has_more"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_message_history_pagination() -> None:
    """Test message history pagination with has_more flag."""
    user_id = uuid4()
    conversation_id = uuid4()
    conv = _MockConversation(id=conversation_id, user_id=user_id)

    # Create 51 messages to trigger has_more (limit + 1)
    messages = [
        _MockChatMessage(
            role="user",
            content_blocks=[{"type": "text", "text": f"Message {i}"}],
        )
        for i in range(51)
    ]

    class _PaginatedMessagesDbSession:
        def __init__(self):
            self._call_count = 0

        async def execute(self, stmt):
            self._call_count += 1
            if self._call_count == 1:
                return _ExecuteResult(single=conv)
            return _ExecuteResult(items=messages)

    db = _PaginatedMessagesDbSession()

    async def _override_get_db():
        yield db

    async def _override_current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_current_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(
                f"/api/v1/chat/conversations/{conversation_id}/messages",
                params={"limit": 50},
            )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        # Should return 50 messages (not 51) with has_more=True
        assert len(body["messages"]) == 50
        assert body["has_more"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
