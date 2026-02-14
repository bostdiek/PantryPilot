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

    def _make_sufficient_messages(
        self, extra_messages: list[dict[str, str]] | None = None
    ) -> list[dict[str, str]]:
        """Create a message list that passes the minimum validation.

        The service requires at least 3 user messages with 120+ total chars.
        """
        base_messages = [
            {"role": "user", "content": "I want to make pasta carbonara tonight"},
            {"role": "assistant", "content": "Great choice! Here's a recipe..."},
            {"role": "user", "content": "What ingredients do I need for this dish?"},
            {"role": "assistant", "content": "You'll need eggs, pancetta, cheese..."},
            {"role": "user", "content": "How long does it take to prepare and cook?"},
            {"role": "assistant", "content": "About 30 minutes total."},
        ]
        if extra_messages:
            return base_messages + extra_messages
        return base_messages

    async def test_generates_title_from_messages(self) -> None:
        """Test generates title from message list."""
        messages = self._make_sufficient_messages()

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

    async def test_limits_messages_by_char_count(self) -> None:
        """Test limits messages by total character count (20000 chars max)."""
        # Create many messages that exceed the 20000 char limit
        messages = self._make_sufficient_messages()
        # Add more messages to test truncation behavior
        for i in range(50):
            content = f"Additional message {i} " * 20
            messages.append({"role": "user", "content": content})

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

            # Check that the agent was called (messages were processed)
            call_args = mock_agent.run.call_args[0][0]
            # First messages should be included
            assert "pasta carbonara" in call_args
            # Total context should be under the limit
            assert len(call_args) <= 21000  # Some buffer for formatting

    async def test_truncates_long_messages(self) -> None:
        """Test truncates message content to 500 characters."""
        long_content = "x" * 1000
        # Start with sufficient messages, then add the long one
        messages = self._make_sufficient_messages()
        messages.append({"role": "user", "content": long_content})

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
            # Content should be truncated to 500 chars
            assert "x" * 500 in call_args
            assert "x" * 501 not in call_args

    async def test_includes_current_title_context(self) -> None:
        """Test includes current title and created_at in context."""
        messages = self._make_sufficient_messages()

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
        messages = self._make_sufficient_messages()

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
        messages = self._make_sufficient_messages()

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
            assert "6 messages" in caplog.text
            assert "Generated title: 🍕 Pizza Night" in caplog.text

    async def test_raises_on_generation_failure(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test raises exception when generation fails."""
        messages = self._make_sufficient_messages()

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
        messages = self._make_sufficient_messages()

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
            assert "user: I want to make pasta carbonara" in call_args
            assert "assistant: Great choice!" in call_args
            assert "Generate a title for:" in call_args

    async def test_returns_none_when_insufficient_messages(self) -> None:
        """Test returns None when fewer than 3 user messages to allow retry later."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        from services.chat_title_generator import generate_conversation_title

        title = await generate_conversation_title(
            messages, current_title="Existing Title"
        )
        # Returns None so scheduler skips this conversation
        # (doesn't set title_updated_at)
        assert title is None

    async def test_returns_none_when_insufficient_messages_no_current_title(
        self,
    ) -> None:
        """Test returns None when <3 user messages, regardless of current_title."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        from services.chat_title_generator import generate_conversation_title

        # Should return None (not raise) to allow retry later
        title = await generate_conversation_title(messages)
        assert title is None

    async def test_skips_messages_with_empty_content(self) -> None:
        """Test skips messages with empty or missing content."""
        messages = self._make_sufficient_messages()
        # Add messages with empty content
        messages.extend(
            [
                {"role": "user", "content": ""},  # Empty content
                {"role": "assistant", "content": None},  # None content
                {"role": "user"},  # Missing content key
            ]
        )

        mock_result = MagicMock()
        mock_result.output.title = "🍲 Test Title"

        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result

        with patch(
            "services.chat_title_generator._get_title_agent",
            return_value=mock_agent,
        ):
            from services.chat_title_generator import generate_conversation_title

            title = await generate_conversation_title(messages)

            assert title == "🍲 Test Title"
            # Verify the empty content messages were not included
            call_args = mock_agent.run.call_args[0][0]
            # Should not have extra empty lines from empty content
            assert "user: \n" not in call_args

    async def test_handles_only_current_title_without_created_at(self) -> None:
        """Test context formatting with current_title but no created_at."""
        messages = self._make_sufficient_messages()

        mock_result = MagicMock()
        mock_result.output.title = "📝 Updated Title"

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
                created_at=None,  # No created_at
            )

            call_args = mock_agent.run.call_args[0][0]
            # Should not include "Current title:" since both are needed
            assert "Current title:" not in call_args
