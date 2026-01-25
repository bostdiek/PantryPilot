"""Tests for chat tool accept/cancel endpoints (Phase 3)."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from dependencies.auth import get_current_user
from dependencies.db import get_db
from main import app
from models.chat_tool_calls import ChatToolCall


class _OneOrNoneResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalars(self) -> _OneOrNoneResult:
        return self

    def one_or_none(self) -> object | None:
        return self._value


class _FakeDbSession:
    def __init__(self, *, action: object | None) -> None:
        self._action = action
        self.added: list[object] = []
        self.commits: int = 0

    async def execute(self, _stmt):
        return _OneOrNoneResult(self._action)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1


def _make_action(
    *, proposal_id: UUID, user_id: UUID, status: str = "proposed"
) -> SimpleNamespace:
    return SimpleNamespace(
        id=proposal_id,
        conversation_id=uuid4(),
        message_id=uuid4(),
        user_id=user_id,
        tool_name="unit_test_tool",
        arguments={"a": 1},
        status=status,
        accepted_at=None,
        canceled_at=None,
        executed_at=None,
        updated_at=None,
        cancel_reason=None,
        error=None,
    )


@pytest.mark.asyncio
async def test_accept_chat_action_happy_path_records_tool_call() -> None:
    user_id = uuid4()
    proposal_id = uuid4()
    action = _make_action(proposal_id=proposal_id, user_id=user_id)
    db = _FakeDbSession(action=action)

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
            resp = await client.post(f"/api/v1/chat/actions/{proposal_id}/accept")

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["proposal_id"] == str(proposal_id)
        assert body["tool_name"] == "unit_test_tool"
        assert body["status"] == "error"
        assert "Tool execution is not implemented" in body["error"]

        # Endpoint should mutate the action state and persist an audit record.
        assert action.status == "failed"
        assert action.error is not None
        assert db.commits == 1

        tool_calls = [obj for obj in db.added if isinstance(obj, ChatToolCall)]
        assert len(tool_calls) == 1
        assert tool_calls[0].tool_name == "unit_test_tool"
        assert tool_calls[0].status == "error"
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_accept_chat_action_404_when_missing() -> None:
    user_id = uuid4()
    proposal_id = uuid4()
    db = _FakeDbSession(action=None)

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
            resp = await client.post(f"/api/v1/chat/actions/{proposal_id}/accept")

        assert resp.status_code == status.HTTP_404_NOT_FOUND
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_cancel_chat_action_happy_path_sets_reason() -> None:
    user_id = uuid4()
    proposal_id = uuid4()
    action = _make_action(proposal_id=proposal_id, user_id=user_id)
    db = _FakeDbSession(action=action)

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
            resp = await client.post(
                f"/api/v1/chat/actions/{proposal_id}/cancel",
                json={"reason": "No longer needed"},
            )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["proposal_id"] == str(proposal_id)
        assert body["status"] == "canceled"
        assert body["cancel_reason"] == "No longer needed"

        assert action.status == "canceled"
        assert action.cancel_reason == "No longer needed"
        assert db.commits == 1
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_cancel_chat_action_conflict_when_not_proposed() -> None:
    user_id = uuid4()
    proposal_id = uuid4()
    action = _make_action(proposal_id=proposal_id, user_id=user_id, status="canceled")
    db = _FakeDbSession(action=action)

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
            resp = await client.post(
                f"/api/v1/chat/actions/{proposal_id}/cancel",
                json={"reason": ""},
            )

        assert resp.status_code == status.HTTP_409_CONFLICT
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
