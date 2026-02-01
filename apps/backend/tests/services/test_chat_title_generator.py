"""Tests for chat title generator service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import models


# Block any real model requests in tests
models.ALLOW_MODEL_REQUESTS = False


class TestGetTitleAgent:
    """Tests for _get_title_agent function.

    Note: Model creation is now handled by the centralized model_factory,
    so we test integration with that instead of testing model creation directly.
    """

    @patch("services.chat_title_generator.Agent")
    @patch("services.chat_title_generator.get_text_model")
    def test_creates_agent_with_correct_config(
        self, mock_get_text_model: MagicMock, mock_agent_class: MagicMock
    ) -> None:
        """Test agent is created using centralized model factory."""
        # Reset global agent
        import services.chat_title_generator

        services.chat_title_generator._title_agent = None

        mock_model = MagicMock()
        mock_get_text_model.return_value = mock_model

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        from services.chat_title_generator import _get_title_agent

        agent = _get_title_agent()
        assert agent is not None
        assert agent == mock_agent_instance
        # Verify Agent was called with model from factory
        mock_agent_class.assert_called_once()
        mock_get_text_model.assert_called_once()

    @patch("services.chat_title_generator.Agent")
    @patch("services.chat_title_generator.get_text_model")
    def test_caches_agent_on_subsequent_calls(
        self, mock_get_text_model: MagicMock, mock_agent_class: MagicMock
    ) -> None:
        """Test agent is cached and reused."""
        # Reset global agent
        import services.chat_title_generator

        services.chat_title_generator._title_agent = None

        mock_model = MagicMock()
        mock_get_text_model.return_value = mock_model

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        from services.chat_title_generator import _get_title_agent

        agent1 = _get_title_agent()
        agent2 = _get_title_agent()

        assert agent1 is agent2
        # Model factory and Agent should only be called once
        assert mock_get_text_model.call_count == 1
        assert mock_agent_class.call_count == 1


@pytest.mark.asyncio
class TestGenerateConversationTitle:
    """Tests for generate_conversation_title function."""

    async def test_generates_title_from_messages(self) -> None:
        """Test generates title from message list."""
        messages = [
            {"role": "user", "content": "I want to make pasta carbonara"},
            {"role": "assistant", "content": "Great choice! Here's a recipe..."},
        ]

        # Mock the agent and result
        mock_result = MagicMock()
        mock_result.output.title = "🍝 Pasta Carbonara Recipe"

        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result

        with patch(
            "services.chat_title_generator._get_title_agent",
            return_value=mock_agent,
        ):
            from services.chat_title_generator import generate_conversation_title

            title = await generate_conversation_title(messages)

            assert title == "🍝 Pasta Carbonara Recipe"
            mock_agent.run.assert_called_once()

    async def test_limits_messages_to_six(self) -> None:
        """Test only uses first 6 messages (3 exchanges)."""
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(20)]

        mock_result = MagicMock()
        mock_result.output.title = "📝 Test Title"

        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result

        with patch(
            "services.chat_title_generator._get_title_agent",
            return_value=mock_agent,
        ):
            from services.chat_title_generator import generate_conversation_title

            await generate_conversation_title(messages)

            # Check that context includes only first 6 messages
            call_args = mock_agent.run.call_args[0][0]
            assert "Message 0" in call_args
            assert "Message 5" in call_args
            assert "Message 6" not in call_args

    async def test_truncates_long_messages(self) -> None:
        """Test truncates message content to 200 characters."""
        long_content = "x" * 500
        messages = [
            {"role": "user", "content": long_content},
            {"role": "assistant", "content": "Short response"},
        ]

        mock_result = MagicMock()
        mock_result.output.title = "📝 Test Title"

        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result

        with patch(
            "services.chat_title_generator._get_title_agent",
            return_value=mock_agent,
        ):
            from services.chat_title_generator import generate_conversation_title

            await generate_conversation_title(messages)

            call_args = mock_agent.run.call_args[0][0]
            # Content should be truncated to 200 chars
            assert "x" * 200 in call_args
            assert "x" * 201 not in call_args

    async def test_includes_current_title_context(self) -> None:
        """Test includes current title and created_at in context."""
        messages = [{"role": "user", "content": "Test message"}]

        mock_result = MagicMock()
        mock_result.output.title = "📝 New Title"

        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result

        with patch(
            "services.chat_title_generator._get_title_agent",
            return_value=mock_agent,
        ):
            from services.chat_title_generator import generate_conversation_title

            await generate_conversation_title(
                messages,
                current_title="Old Title",
                created_at="2026-01-31T10:00:00Z",
            )

            call_args = mock_agent.run.call_args[0][0]
            assert "Old Title" in call_args
            assert "2026-01-31T10:00:00Z" in call_args

    async def test_works_without_current_title(self) -> None:
        """Test generates title without current title context."""
        messages = [{"role": "user", "content": "Test message"}]

        mock_result = MagicMock()
        mock_result.output.title = "📝 New Title"

        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result

        with patch(
            "services.chat_title_generator._get_title_agent",
            return_value=mock_agent,
        ):
            from services.chat_title_generator import generate_conversation_title

            title = await generate_conversation_title(messages)

            assert title == "📝 New Title"
            call_args = mock_agent.run.call_args[0][0]
            assert "Current title:" not in call_args

    async def test_logs_generation_info(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logs information about title generation."""
        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Message 2"},
        ]

        mock_result = MagicMock()
        mock_result.output.title = "🍕 Pizza Night"

        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result

        with patch(
            "services.chat_title_generator._get_title_agent",
            return_value=mock_agent,
        ):
            from services.chat_title_generator import generate_conversation_title

            await generate_conversation_title(messages)

            assert "Generating title" in caplog.text
            assert "2 messages" in caplog.text
            assert "Generated title: 🍕 Pizza Night" in caplog.text

    async def test_raises_on_generation_failure(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test raises exception when generation fails."""
        messages = [{"role": "user", "content": "Test"}]

        mock_agent = AsyncMock()
        mock_agent.run.side_effect = Exception("API error")

        with patch(
            "services.chat_title_generator._get_title_agent",
            return_value=mock_agent,
        ):
            from services.chat_title_generator import generate_conversation_title

            with pytest.raises(Exception, match="API error"):
                await generate_conversation_title(messages)

            assert "Failed to generate conversation title" in caplog.text

    async def test_formats_context_correctly(self) -> None:
        """Test context formatting includes role and content."""
        messages = [
            {"role": "user", "content": "What's for dinner?"},
            {"role": "assistant", "content": "How about tacos?"},
        ]

        mock_result = MagicMock()
        mock_result.output.title = "🌮 Taco Tuesday"

        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result

        with patch(
            "services.chat_title_generator._get_title_agent",
            return_value=mock_agent,
        ):
            from services.chat_title_generator import generate_conversation_title

            await generate_conversation_title(messages)

            call_args = mock_agent.run.call_args[0][0]
            assert "user: What's for dinner?" in call_args
            assert "assistant: How about tacos?" in call_args
            assert "Generate a title for:" in call_args
