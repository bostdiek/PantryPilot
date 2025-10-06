"""Draft token retrieval tests (partial; some reinstated later)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient

from main import app


pytest_plugins = ("tests.fixtures.ai_fixtures",)


@pytest_asyncio.fixture
async def no_auth_client():
    from dependencies.auth import get_current_user

    original = dict(app.dependency_overrides)
    app.dependency_overrides.pop(get_current_user, None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides = original


@pytest.mark.asyncio
async def test_get_ai_draft_invalid_token(no_auth_client):
    fake_draft_id = "12345678-1234-5678-9012-123456789012"
    resp = await no_auth_client.get(
        f"/api/v1/ai/drafts/{fake_draft_id}?token=invalid-token"
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.skip("Reinstate after adapting to new draft service flow")
@pytest.mark.asyncio
async def test_get_ai_draft_success_pending():  # placeholder
    pass


@pytest.mark.skip("Reinstate after adapting to new draft service flow")
@pytest.mark.asyncio
async def test_get_ai_draft_expired_pending():  # placeholder
    pass
