"""API tests for non-streaming AI recipe extraction endpoint."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient

from main import app


pytest_plugins = ("tests.fixtures.ai_fixtures",)


@pytest_asyncio.fixture
async def no_auth_client():  # local helper
    from dependencies.auth import get_current_user

    original = dict(app.dependency_overrides)
    app.dependency_overrides.pop(get_current_user, None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides = original


@pytest.mark.asyncio
async def test_extract_recipe_from_url_success(
    async_client: AsyncClient,
    sample_extraction_result,
    sample_ai_generated_recipe,
    mock_recipe_html,
) -> None:
    """Happy path: ensure contract fields present (acts like a lightweight snapshot)."""
    with (
        patch(
            "services.ai.orchestrator.HTMLExtractorAdapter.fetch_sanitized_html",
            return_value=mock_recipe_html,
        ),
        patch(
            "services.ai.orchestrator.AIAgentAdapter.run_extraction_agent",
            return_value=sample_extraction_result,
        ),
        patch(
            "services.ai.agents.convert_to_recipe_create",
            return_value=sample_ai_generated_recipe,
        ),
    ):
        resp = await async_client.post(
            "/api/v1/ai/extract-recipe-from-url",
            json={"source_url": "https://example.com/recipe"},
        )

    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    # Stable contract keys
    for key in ("draft_id", "signed_url", "expires_at", "ttl_seconds"):
        assert key in data
    assert data["ttl_seconds"] == 3600


@pytest.mark.asyncio
async def test_extract_recipe_from_url_invalid_url(
    async_client: AsyncClient, invalid_url
) -> None:
    resp = await async_client.post(
        "/api/v1/ai/extract-recipe-from-url", json={"source_url": invalid_url}
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_extract_recipe_from_url_not_found(
    async_client: AsyncClient, extraction_not_found, mock_non_recipe_html
) -> None:
    from uuid import uuid4

    with (
        patch(
            "services.ai.orchestrator.HTMLExtractorAdapter.fetch_sanitized_html",
            return_value=mock_non_recipe_html,
        ),
        patch(
            "services.ai.orchestrator.AIAgentAdapter.run_extraction_agent",
            return_value=extraction_not_found,
        ),
        patch("services.ai.orchestrator.create_failure_draft") as mock_failure,
        patch(
            "services.ai.draft_service.create_draft_token", return_value="test-token"
        ),
    ):
        from datetime import datetime, timedelta

        mock_draft = type(
            "Draft",
            (),
            {
                "id": str(uuid4()),
                "expires_at": datetime.now(UTC) + timedelta(hours=1),
            },
        )()
        mock_failure.return_value = mock_draft
        resp = await async_client.post(
            "/api/v1/ai/extract-recipe-from-url",
            json={"source_url": "https://example.com/not-a-recipe"},
        )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["success"] is False
    assert body["message"] == "Recipe not found"
    data = body["data"]
    assert "draft_id" in data and "signed_url" in data


@pytest.mark.asyncio
async def test_extract_recipe_from_url_ai_failure(
    async_client: AsyncClient, mock_recipe_html, mock_agent_run_error
) -> None:
    with (
        patch(
            "services.ai.orchestrator.HTMLExtractorAdapter.fetch_sanitized_html",
            return_value=mock_recipe_html,
        ),
        patch(
            "services.ai.orchestrator.AIAgentAdapter.run_extraction_agent",
            side_effect=mock_agent_run_error,
        ),
    ):
        resp = await async_client.post(
            "/api/v1/ai/extract-recipe-from-url",
            json={"source_url": "https://example.com/recipe"},
        )
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = resp.json()["detail"]
    assert detail == "An unexpected error occurred during recipe extraction"


@pytest.mark.asyncio
async def test_extract_recipe_from_url_unauthorized(
    no_auth_client: AsyncClient, valid_recipe_url
) -> None:
    resp = await no_auth_client.post(
        "/api/v1/ai/extract-recipe-from-url", json={"source_url": valid_recipe_url}
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
