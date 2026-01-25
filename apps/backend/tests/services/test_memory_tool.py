"""Tests for the memory update tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.chat_agent.tools.memory import tool_update_user_memory


@pytest.fixture
def mock_ctx():
    """Create a mock RunContext with ChatAgentDeps."""
    ctx = MagicMock()
    ctx.deps.user.id = uuid4()
    return ctx


@pytest.fixture
def mock_memory_doc():
    """Create a mock UserMemoryDocument."""
    doc = MagicMock()
    doc.version = 2
    doc.content = "## Test Memory"
    return doc


@pytest.mark.asyncio
async def test_update_user_memory_success(mock_ctx, mock_memory_doc):
    """Test successful memory update."""
    with patch(
        "services.chat_agent.tools.memory.AsyncSessionLocal"
    ) as mock_session_factory:
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session_factory.return_value = mock_session

        with patch(
            "services.chat_agent.tools.memory.MemoryUpdateService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.update_memory_content.return_value = mock_memory_doc
            mock_service_class.return_value = mock_service

            result = await tool_update_user_memory(
                mock_ctx, memory_content="## New Memory\n- Item 1"
            )

            assert result["status"] == "ok"
            assert result["version"] == 2
            assert "Memory updated successfully" in result["message"]
            mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_memory_error_handling(mock_ctx):
    """Test error handling when update fails."""
    with patch(
        "services.chat_agent.tools.memory.AsyncSessionLocal"
    ) as mock_session_factory:
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session_factory.return_value = mock_session

        with patch(
            "services.chat_agent.tools.memory.MemoryUpdateService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.update_memory_content.side_effect = Exception("DB error")
            mock_service_class.return_value = mock_service

            result = await tool_update_user_memory(mock_ctx, memory_content="## Memory")

            assert result["status"] == "error"
            assert "Failed to update memory" in result["message"]
