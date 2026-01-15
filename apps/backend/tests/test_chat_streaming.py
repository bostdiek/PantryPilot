"""Tests for chat streaming endpoint."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from pydantic_ai import models
from pydantic_ai.models.test import TestModel


# Block any real model requests in tests
models.ALLOW_MODEL_REQUESTS = False


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
