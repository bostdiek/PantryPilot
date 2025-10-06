"""API tests for streaming AI recipe extraction endpoint (SSE)."""

from __future__ import annotations

import json
from contextlib import ExitStack
from typing import Any
from unittest.mock import Mock, patch

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient

from main import app


# Constants to avoid overlong lines in parametrized patches
FETCH_HTML = "services.ai.orchestrator.HTMLExtractorAdapter.fetch_sanitized_html"
RUN_AGENT = "services.ai.orchestrator.AIAgentAdapter.run_extraction_agent"


pytest_plugins = ("tests.fixtures.ai_fixtures",)


@pytest_asyncio.fixture
async def no_auth_client():  # duplication intentional for isolation
    from dependencies.auth import get_current_user

    original = dict(app.dependency_overrides)
    app.dependency_overrides.pop(get_current_user, None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides = original


def _parse_sse(raw: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in raw.split("\n"):
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                continue
    return events


@pytest.mark.asyncio
async def test_stream_success_terminal(
    async_client: AsyncClient,
    sample_extraction_result,
    sample_ai_generated_recipe,
    mock_recipe_html,
) -> None:
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
        resp = await async_client.get(
            "/api/v1/ai/extract-recipe-stream?source_url=https://example.com/recipe"
        )

    assert resp.status_code == status.HTTP_200_OK
    events = _parse_sse(resp.text)
    assert events, "Expected at least one SSE event"
    final = events[-1]
    assert final["status"] in {"complete", "error"}
    if final["status"] == "complete":
        assert final["success"] is True
        for k in ("draft_id", "progress", "step"):
            assert k in final
        assert final["progress"] == 1.0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_kind,patches,expected_step,detail_substring",
    [
        (
            "fetch_failure",
            {FETCH_HTML: Exception("Network error")},
            "fetch_html",
            "Fetch failed",
        ),
        (
            "no_html",
            {FETCH_HTML: ""},
            "fetch_html",
            "No usable HTML content",
        ),
        (
            "ai_failure",
            {
                FETCH_HTML: "<html></html>",
                RUN_AGENT: Exception("Agent crash"),
            },
            "ai_call",
            "AI agent failure",
        ),
        (
            "conversion_failure",
            {
                FETCH_HTML: "<html></html>",
                RUN_AGENT: "invalid_type",
            },
            "convert_schema",
            "Conversion failed",
        ),
    ],
)
async def test_stream_error_variants(
    async_client: AsyncClient,
    failure_kind,
    patches,
    expected_step,
    detail_substring,
):
    ctx_managers = []
    for target, value in patches.items():
        if isinstance(value, Exception):
            ctx_managers.append(patch(target, side_effect=value))
        else:
            ctx_managers.append(patch(target, return_value=value))
    with ExitStack() as es:
        for cm in ctx_managers:
            es.enter_context(cm)
        resp = await async_client.get(
            "/api/v1/ai/extract-recipe-stream?source_url=https://example.com/recipe"
        )

    assert resp.status_code == status.HTTP_200_OK
    events = _parse_sse(resp.text)
    assert events[-1]["status"] == "error"
    assert events[-1]["step"] == expected_step
    assert detail_substring in events[-1]["detail"]
    assert events[-1]["progress"] == 1.0


@pytest.mark.asyncio
async def test_stream_not_found(async_client: AsyncClient) -> None:
    from schemas.ai import ExtractionNotFound

    mock_html = "<html><body><h1>Not a recipe</h1></body></html>"
    with ExitStack() as es:
        es.enter_context(
            patch(
                "services.ai.orchestrator.HTMLExtractorAdapter.fetch_sanitized_html",
                return_value=mock_html,
            )
        )
        es.enter_context(
            patch(
                "services.ai.orchestrator.AIAgentAdapter.run_extraction_agent",
                return_value=ExtractionNotFound(reason="No recipe here"),
            )
        )
        mock_failure = es.enter_context(
            patch("services.ai.draft_service.create_failure_draft")
        )
        es.enter_context(
            patch("services.ai.draft_service.create_draft_token", return_value="tok")
        )
        mock_draft = Mock()
        mock_draft.id = "d1"  # noqa: E702 (compact acceptable)
        mock_failure.return_value = mock_draft
        resp = await async_client.get(
            "/api/v1/ai/extract-recipe-stream?source_url=https://example.com/search"
        )

    events = _parse_sse(resp.text)
    final = events[-1]
    assert final["status"] == "complete"
    assert final["success"] is False
    assert "draft_id" in final


@pytest.mark.asyncio
async def test_stream_prompt_override(
    async_client: AsyncClient, sample_extraction_result, sample_ai_generated_recipe
) -> None:
    mock_html = "<html><body><h1>Mock Recipe</h1></body></html>"
    with (
        patch(
            "services.ai.orchestrator.HTMLExtractorAdapter.fetch_sanitized_html",
            return_value=mock_html,
        ),
        patch(
            "services.ai.orchestrator.AIAgentAdapter.run_extraction_agent",
            return_value=sample_extraction_result,
        ) as mock_run,
        patch(
            "services.ai.agents.convert_to_recipe_create",
            return_value=sample_ai_generated_recipe,
        ),
    ):
        custom_prompt = "Extract only the ingredients from this page"
        resp = await async_client.get(
            f"/api/v1/ai/extract-recipe-stream?source_url=https://example.com/recipe&prompt_override={custom_prompt}"
        )
    assert resp.status_code == status.HTTP_200_OK
    args, _ = mock_run.call_args
    assert len(args) >= 2 and args[1] == custom_prompt


@pytest.mark.asyncio
async def test_stream_unauthorized(no_auth_client: AsyncClient) -> None:
    resp = await no_auth_client.get(
        "/api/v1/ai/extract-recipe-stream?source_url=https://example.com/recipe"
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
