"""Focused lifecycle tests for recipe-contextual conversations."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.sql.dml import Update

from dependencies.auth import get_current_user
from dependencies.db import get_db
from main import app
from models.chat_conversations import ChatConversation


class _ScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def one_or_none(self) -> Any:
        return self._value


class _ExecuteResult:
    def __init__(self, value: Any = None) -> None:
        self._value = value

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._value)


class _ScriptedSession:
    def __init__(
        self,
        select_results: list[Any],
        conversations: list[Any] | None = None,
    ) -> None:
        self.select_results = list(select_results)
        self.conversations = conversations or []
        self.added: list[Any] = []
        self.deleted: list[Any] = []
        self.commits = 0
        self.mutation_events: list[str] = []

    async def execute(self, statement: Any) -> _ExecuteResult:
        if isinstance(statement, Update):
            for conversation in self.conversations:
                conversation.is_current_for_recipe = False
            return _ExecuteResult()
        return _ExecuteResult(self.select_results.pop(0))

    def add(self, conversation: Any) -> None:
        now = datetime.now(UTC)
        conversation.id = conversation.id or uuid4()
        conversation.created_at = conversation.created_at or now
        conversation.updated_at = conversation.updated_at or now
        conversation.last_activity_at = conversation.last_activity_at or now
        self.added.append(conversation)
        self.conversations.append(conversation)

    async def flush(self) -> None:
        self.mutation_events.append("flush")

    async def commit(self) -> None:
        self.mutation_events.append("commit")
        self.commits += 1

    async def refresh(self, _conversation: Any) -> None:
        return None

    async def delete(self, conversation: Any) -> None:
        self.mutation_events.append("delete")
        self.deleted.append(conversation)
        if conversation in self.conversations:
            self.conversations.remove(conversation)


def _recipe(recipe_id: UUID, user_id: UUID) -> SimpleNamespace:
    return SimpleNamespace(id=recipe_id, user_id=user_id, name="Tomato Soup")


def _conversation(
    *,
    conversation_id: UUID | None = None,
    user_id: UUID,
    recipe_id: UUID,
    current: bool,
    title: str,
) -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=conversation_id or uuid4(),
        user_id=user_id,
        recipe_id=recipe_id,
        is_current_for_recipe=current,
        title=title,
        created_at=now,
        last_activity_at=now,
    )


async def _post(
    path: str,
    *,
    user_id: UUID,
    db: _ScriptedSession,
) -> tuple[int, dict[str, Any]]:
    async def _override_get_db():
        yield db

    async def _override_current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_current_user
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(path)
        return response.status_code, response.json()
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_chat_conversation_model_declares_recipe_context_invariants() -> None:
    recipe_id = ChatConversation.__table__.c.recipe_id
    current = ChatConversation.__table__.c.is_current_for_recipe
    current_index = next(
        index
        for index in ChatConversation.__table__.indexes
        if index.name == "uq_chat_conversations_current_recipe"
    )

    assert recipe_id.nullable is True
    assert {
        (foreign_key.target_fullname, foreign_key.ondelete)
        for foreign_key in recipe_id.foreign_keys
    } == {("recipe_names.id", "CASCADE")}
    assert current.nullable is False
    assert str(current.server_default.arg) == "false"
    assert current_index.unique is True
    assert str(current_index.dialect_options["postgresql"]["where"]) == (
        "chat_conversations.recipe_id IS NOT NULL "
        "AND chat_conversations.is_current_for_recipe"
    )


@pytest.mark.asyncio
async def test_resume_recipe_conversation_is_idempotent() -> None:
    user_id = uuid4()
    recipe_id = uuid4()
    recipe = _recipe(recipe_id, user_id)
    db = _ScriptedSession([recipe, None, recipe])

    first_status, first = await _post(
        f"/api/v1/chat/recipes/{recipe_id}/conversations/resume",
        user_id=user_id,
        db=db,
    )
    db.select_results.append(db.added[0])
    second_status, second = await _post(
        f"/api/v1/chat/recipes/{recipe_id}/conversations/resume",
        user_id=user_id,
        db=db,
    )

    assert first_status == status.HTTP_200_OK
    assert second_status == status.HTTP_200_OK
    assert first["id"] == second["id"]
    assert first["recipe_context"] == {
        "recipe_id": str(recipe_id),
        "recipe_title": "Tomato Soup",
        "is_current": True,
    }
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_resume_hides_missing_and_cross_user_recipes() -> None:
    user_id = uuid4()
    db = _ScriptedSession([None, None])

    missing_status, missing = await _post(
        f"/api/v1/chat/recipes/{uuid4()}/conversations/resume",
        user_id=user_id,
        db=db,
    )
    cross_user_status, cross_user = await _post(
        f"/api/v1/chat/recipes/{uuid4()}/conversations/resume",
        user_id=user_id,
        db=db,
    )

    assert missing_status == status.HTTP_404_NOT_FOUND
    assert cross_user_status == status.HTTP_404_NOT_FOUND
    assert missing == cross_user == {"detail": "Recipe not found"}
    assert db.added == []


@pytest.mark.asyncio
async def test_create_recipe_conversation_always_starts_a_distinct_thread() -> None:
    user_id = uuid4()
    recipe_id = uuid4()
    recipe = _recipe(recipe_id, user_id)
    db = _ScriptedSession([recipe, recipe])

    first_status, first = await _post(
        f"/api/v1/chat/recipes/{recipe_id}/conversations",
        user_id=user_id,
        db=db,
    )
    second_status, second = await _post(
        f"/api/v1/chat/recipes/{recipe_id}/conversations",
        user_id=user_id,
        db=db,
    )

    assert first_status == status.HTTP_201_CREATED
    assert second_status == status.HTTP_201_CREATED
    assert first["id"] != second["id"]
    assert [item.is_current_for_recipe for item in db.added] == [False, True]


@pytest.mark.asyncio
async def test_select_older_recipe_conversation_makes_it_current() -> None:
    user_id = uuid4()
    recipe_id = uuid4()
    recipe = _recipe(recipe_id, user_id)
    current = _conversation(
        user_id=user_id,
        recipe_id=recipe_id,
        current=True,
        title="Current",
    )
    older = _conversation(
        user_id=user_id,
        recipe_id=recipe_id,
        current=False,
        title="Older",
    )
    db = _ScriptedSession([older, recipe, older], [current, older])

    response_status, body = await _post(
        f"/api/v1/chat/conversations/{older.id}/select",
        user_id=user_id,
        db=db,
    )

    assert response_status == status.HTTP_200_OK
    assert body["id"] == str(older.id)
    assert body["recipe_context"]["is_current"] is True
    assert current.is_current_for_recipe is False
    assert older.is_current_for_recipe is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "conversation",
    [
        None,
        SimpleNamespace(recipe_id=None),
    ],
    ids=["unowned-or-missing", "general-conversation"],
)
async def test_select_hides_unowned_and_general_conversations(
    conversation: SimpleNamespace | None,
) -> None:
    db = _ScriptedSession([conversation])

    response_status, body = await _post(
        f"/api/v1/chat/conversations/{uuid4()}/select",
        user_id=uuid4(),
        db=db,
    )

    assert response_status == status.HTTP_404_NOT_FOUND
    assert body == {"detail": "Conversation not found"}
    assert db.commits == 0


@pytest.mark.asyncio
async def test_delete_current_recipe_conversation_promotes_latest_remaining() -> None:
    user_id = uuid4()
    recipe_id = uuid4()
    recipe = _recipe(recipe_id, user_id)
    current = _conversation(
        user_id=user_id,
        recipe_id=recipe_id,
        current=True,
        title="Current",
    )
    replacement = _conversation(
        user_id=user_id,
        recipe_id=recipe_id,
        current=False,
        title="Replacement",
    )
    db = _ScriptedSession(
        [current, recipe, current, replacement],
        [current, replacement],
    )

    async def _override_get_db():
        yield db

    async def _override_current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_current_user
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.delete(f"/api/v1/chat/conversations/{current.id}")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert db.deleted == [current]
    assert db.mutation_events == ["flush", "delete", "commit"]
    assert current.is_current_for_recipe is False
    assert replacement.is_current_for_recipe is True
