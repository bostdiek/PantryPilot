"""Ordered SSE stream contract tests.

Ensures the orchestrator emits a stable, ordered sequence of SSE events for the
happy-path success flow and the not-found flow. This guards against accidental
reordering or omission of steps which would break frontend progress UIs.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi import status
from httpx import AsyncClient


EXPECTED_SUCCESS_STEPS = [
    ("started", "started"),
    ("fetching", "fetch_html"),
    ("sanitizing", "sanitize_html"),
    ("ai_call", "ai_call"),
    ("converting", "convert_schema"),
    ("complete", "complete"),
]

EXPECTED_NOT_FOUND_STEPS = [
    ("started", "started"),
    ("fetching", "fetch_html"),
    ("sanitizing", "sanitize_html"),
    ("ai_call", "ai_call"),
    ("complete", "complete"),  # failure terminal success (success=false)
]


@pytest.mark.asyncio
async def test_stream_order_success(
    async_client: AsyncClient,
    sample_extraction_result,
    sample_ai_generated_recipe,
    mock_recipe_html,
):  # noqa: D401
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
    events = [
        json.loads(line[6:])
        for line in resp.text.split("\n")
        if line.startswith("data: ")
    ]
    got = [(e["status"], e["step"]) for e in events]
    assert got == EXPECTED_SUCCESS_STEPS, got
    # Terminal invariants
    final = events[-1]
    assert final["success"] is True
    assert final["progress"] == 1.0


@pytest.mark.asyncio
async def test_stream_order_not_found(async_client: AsyncClient, mock_recipe_html):  # noqa: D401
    from schemas.ai import ExtractionNotFound

    not_found = ExtractionNotFound(reason="none")
    with (
        patch(
            "services.ai.orchestrator.HTMLExtractorAdapter.fetch_sanitized_html",
            return_value=mock_recipe_html,
        ),
        patch(
            "services.ai.orchestrator.AIAgentAdapter.run_extraction_agent",
            return_value=not_found,
        ),
    ):
        resp = await async_client.get(
            "/api/v1/ai/extract-recipe-stream?source_url=https://example.com/recipe"
        )

    assert resp.status_code == status.HTTP_200_OK
    events = [
        json.loads(line[6:])
        for line in resp.text.split("\n")
        if line.startswith("data: ")
    ]
    got = [(e["status"], e["step"]) for e in events]
    assert got == EXPECTED_NOT_FOUND_STEPS, got
    final = events[-1]
    assert final["success"] is False
    assert final["progress"] == 1.0
