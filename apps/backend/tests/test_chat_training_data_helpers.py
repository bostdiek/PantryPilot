"""Tests for chat.py training data helpers and utility functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)


class TestProcessModelRequestForTraining:
    """Tests for _process_model_request_for_training."""

    def test_skips_system_prompt_part(self) -> None:
        """Test that SystemPromptPart is skipped."""
        from api.v1.chat import _process_model_request_for_training

        part = SystemPromptPart(content="You are a helpful assistant")
        msg = ModelRequest(parts=[part])
        seen: set[str] = set()

        result = _process_model_request_for_training(msg, seen)

        assert result == []

    def test_processes_user_prompt_part(self) -> None:
        """Test that UserPromptPart is processed correctly."""
        from api.v1.chat import _process_model_request_for_training

        part = UserPromptPart(content="What is for dinner?", timestamp=None)
        msg = ModelRequest(parts=[part])
        seen: set[str] = set()

        result = _process_model_request_for_training(msg, seen)

        assert len(result) == 1
        assert result[0] == {"role": "user", "content": "What is for dinner?"}

    def test_deduplicates_user_messages(self) -> None:
        """Test that duplicate user messages are skipped."""
        from api.v1.chat import _process_model_request_for_training

        part = UserPromptPart(content="What is for dinner?", timestamp=None)
        msg = ModelRequest(parts=[part])
        seen: set[str] = {"What is for dinner?"}  # Already seen

        result = _process_model_request_for_training(msg, seen)

        assert result == []

    def test_processes_tool_return_part(self) -> None:
        """Test that ToolReturnPart is processed correctly."""
        from api.v1.chat import _process_model_request_for_training

        part = ToolReturnPart(
            tool_name="search_recipes",
            tool_call_id="call-123",
            content={"recipes": []},
            timestamp=None,
        )
        msg = ModelRequest(parts=[part])
        seen: set[str] = set()

        result = _process_model_request_for_training(msg, seen)

        assert len(result) == 1
        assert result[0]["role"] == "tool"
        assert result[0]["tool_call_id"] == "call-123"

    def test_processes_multiple_parts(self) -> None:
        """Test processing multiple parts in a single request."""
        from api.v1.chat import _process_model_request_for_training

        parts = [
            SystemPromptPart(content="System prompt"),  # Should be skipped
            UserPromptPart(content="First message", timestamp=None),
            ToolReturnPart(
                tool_name="test",
                tool_call_id="call-1",
                content="result",
                timestamp=None,
            ),
        ]
        msg = ModelRequest(parts=parts)
        seen: set[str] = set()

        result = _process_model_request_for_training(msg, seen)

        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "tool"


class TestProcessModelResponseForTraining:
    """Tests for _process_model_response_for_training."""

    def test_processes_text_part(self) -> None:
        """Test that TextPart is processed correctly."""
        from api.v1.chat import _process_model_response_for_training

        part = TextPart(content="Here are some recipe ideas")
        msg = ModelResponse(parts=[part], usage=None, model_name=None, timestamp=None)

        result = _process_model_response_for_training(msg)

        assert result is not None
        assert result["role"] == "assistant"
        assert result["content"] == "Here are some recipe ideas"

    def test_processes_tool_call_part(self) -> None:
        """Test that ToolCallPart is processed correctly."""
        from api.v1.chat import _process_model_response_for_training

        part = ToolCallPart(
            tool_name="search_recipes",
            tool_call_id="call-123",
            args={"query": "chicken"},
        )
        msg = ModelResponse(parts=[part], usage=None, model_name=None, timestamp=None)

        result = _process_model_response_for_training(msg)

        assert result is not None
        assert result["role"] == "assistant"
        assert "tool_calls" in result
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["function"]["name"] == "search_recipes"

    def test_combines_text_and_tool_calls(self) -> None:
        """Test combining text and tool calls in one response."""
        from api.v1.chat import _process_model_response_for_training

        parts = [
            TextPart(content="Let me search for recipes"),
            ToolCallPart(
                tool_name="search_recipes",
                tool_call_id="call-123",
                args={"query": "pasta"},
            ),
        ]
        msg = ModelResponse(parts=parts, usage=None, model_name=None, timestamp=None)

        result = _process_model_response_for_training(msg)

        assert result is not None
        assert result["content"] == "Let me search for recipes"
        assert len(result["tool_calls"]) == 1

    def test_returns_none_for_empty_response(self) -> None:
        """Test returns None when no content or tool calls."""
        from api.v1.chat import _process_model_response_for_training

        # Empty text parts should be skipped
        part = TextPart(content="")
        msg = ModelResponse(parts=[part], usage=None, model_name=None, timestamp=None)

        result = _process_model_response_for_training(msg)

        assert result is None

    def test_returns_none_for_no_parts(self) -> None:
        """Test returns None when no parts at all."""
        from api.v1.chat import _process_model_response_for_training

        msg = ModelResponse(parts=[], usage=None, model_name=None, timestamp=None)

        result = _process_model_response_for_training(msg)

        assert result is None


class TestBuildTrainingPromptData:
    """Tests for _build_training_prompt_data."""

    def test_prepends_system_prompt(self) -> None:
        """Test that CHAT_SYSTEM_PROMPT is prepended."""
        from api.v1.chat import _build_training_prompt_data

        mock_result = MagicMock()
        mock_result.all_messages.return_value = []

        result = _build_training_prompt_data(mock_result)

        assert len(result) >= 1
        assert result[0]["role"] == "system"

    def test_handles_missing_all_messages(self) -> None:
        """Test handles objects without all_messages method."""
        from api.v1.chat import _build_training_prompt_data

        mock_result = MagicMock(spec=[])  # No all_messages

        result = _build_training_prompt_data(mock_result)

        # Should still have system prompt
        assert len(result) == 1
        assert result[0]["role"] == "system"


class TestSerializeRawOutputForTraining:
    """Tests for _serialize_raw_output_for_training."""

    def test_serializes_pydantic_model(self) -> None:
        """Test serializing object with model_dump method."""
        from api.v1.chat import _serialize_raw_output_for_training

        mock_output = MagicMock()
        mock_output.model_dump.return_value = {"key": "value"}

        result = _serialize_raw_output_for_training(mock_output)

        assert result == '{"key": "value"}'

    def test_serializes_dict(self) -> None:
        """Test serializing a plain dictionary."""
        from api.v1.chat import _serialize_raw_output_for_training

        result = _serialize_raw_output_for_training({"foo": "bar"})

        assert result == '{"foo": "bar"}'

    def test_serializes_string(self) -> None:
        """Test serializing a string."""
        from api.v1.chat import _serialize_raw_output_for_training

        result = _serialize_raw_output_for_training("plain text")

        assert result == "plain text"

    def test_handles_non_serializable_model_dump(self) -> None:
        """Test fallback when model_dump result is not serializable."""
        from api.v1.chat import _serialize_raw_output_for_training

        mock_output = MagicMock()
        # model_dump returns non-serializable object
        mock_output.model_dump.return_value = {"func": lambda x: x}

        result = _serialize_raw_output_for_training(mock_output)

        # Should fallback to str()
        assert isinstance(result, str)


class TestGetTokensFromUsage:
    """Tests for _get_tokens_from_usage."""

    def test_extracts_from_dict_prompt_tokens(self) -> None:
        """Test extracting prompt_tokens from dict."""
        from api.v1.chat import _get_tokens_from_usage

        usage = {"prompt_tokens": 100, "completion_tokens": 50}

        prompt, completion = _get_tokens_from_usage(usage)

        assert prompt == 100
        assert completion == 50

    def test_extracts_from_dict_input_tokens(self) -> None:
        """Test extracting input_tokens from dict (Azure/Anthropic style)."""
        from api.v1.chat import _get_tokens_from_usage

        usage = {"input_tokens": 100, "output_tokens": 50}

        prompt, completion = _get_tokens_from_usage(usage)

        assert prompt == 100
        assert completion == 50

    def test_extracts_from_object_attributes(self) -> None:
        """Test extracting from object attributes."""
        from api.v1.chat import _get_tokens_from_usage

        usage = MagicMock()
        usage.prompt_tokens = 200
        usage.completion_tokens = 100

        prompt, completion = _get_tokens_from_usage(usage)

        assert prompt == 200
        assert completion == 100

    def test_extracts_from_object_input_tokens(self) -> None:
        """Test extracting input_tokens from object."""
        from api.v1.chat import _get_tokens_from_usage

        usage = MagicMock(spec=["input_tokens", "output_tokens"])
        usage.input_tokens = 150
        usage.output_tokens = 75

        prompt, completion = _get_tokens_from_usage(usage)

        assert prompt == 150
        assert completion == 75

    def test_returns_none_for_missing_fields(self) -> None:
        """Test returns None when fields are missing."""
        from api.v1.chat import _get_tokens_from_usage

        usage = {}

        prompt, completion = _get_tokens_from_usage(usage)

        assert prompt is None
        assert completion is None


class TestSumUsageFromMessages:
    """Tests for _sum_usage_from_messages."""

    def test_sums_usage_from_model_responses(self) -> None:
        """Test summing usage from multiple ModelResponse messages."""
        from api.v1.chat import _sum_usage_from_messages

        usage1 = MagicMock()
        usage1.prompt_tokens = 100
        usage1.completion_tokens = 50
        msg1 = ModelResponse(parts=[], usage=usage1, model_name=None, timestamp=None)

        usage2 = MagicMock()
        usage2.prompt_tokens = 200
        usage2.completion_tokens = 100
        msg2 = ModelResponse(parts=[], usage=usage2, model_name=None, timestamp=None)

        mock_result = MagicMock()
        mock_result.all_messages.return_value = [msg1, msg2]

        total_input, total_output = _sum_usage_from_messages(mock_result)

        assert total_input == 300
        assert total_output == 150

    def test_handles_missing_all_messages(self) -> None:
        """Test handles objects without all_messages method."""
        from api.v1.chat import _sum_usage_from_messages

        mock_result = MagicMock(spec=[])

        total_input, total_output = _sum_usage_from_messages(mock_result)

        assert total_input == 0
        assert total_output == 0


class TestExtractUsageMetrics:
    """Tests for _extract_usage_metrics."""

    def test_returns_none_for_none_result(self) -> None:
        """Test returns None tuple for None agent result."""
        from api.v1.chat import _extract_usage_metrics

        result = _extract_usage_metrics(None)

        assert result == (None, None, None)

    def test_extracts_from_direct_usage(self) -> None:
        """Test extracting from agent_result.usage directly."""
        from api.v1.chat import _extract_usage_metrics

        usage = MagicMock()
        usage.prompt_tokens = 100
        usage.completion_tokens = 50

        mock_result = MagicMock()
        mock_result.usage = usage

        result = _extract_usage_metrics(mock_result)

        assert result == (100, 50, None)

    def test_falls_back_to_message_sum(self) -> None:
        """Test falling back to summing from messages."""
        from api.v1.chat import _extract_usage_metrics

        usage = MagicMock()
        usage.prompt_tokens = 100
        usage.completion_tokens = 50
        msg = ModelResponse(parts=[], usage=usage, model_name=None, timestamp=None)

        mock_result = MagicMock()
        mock_result.usage = None  # No direct usage
        mock_result.all_messages.return_value = [msg]

        result = _extract_usage_metrics(mock_result)

        assert result == (100, 50, None)


class TestExtractModelMetadata:
    """Tests for _extract_model_metadata."""

    def test_extracts_from_agent_result(self) -> None:
        """Test extracting model name and version from result."""
        from api.v1.chat import _extract_model_metadata

        mock_result = MagicMock()
        mock_result.model_name = "gpt-4"
        mock_result.model_version = "0613"

        name, version = _extract_model_metadata(mock_result)

        assert name == "gpt-4"
        assert version == "0613"

    def test_falls_back_to_settings(self) -> None:
        """Test falling back to settings when result has no model info."""
        from api.v1.chat import _extract_model_metadata

        mock_result = MagicMock()
        mock_result.model_name = None

        with patch("api.v1.chat.get_settings") as mock_settings:
            mock_settings.return_value.LLM_PROVIDER = "openai"
            mock_settings.return_value.CHAT_MODEL = "gpt-4"

            name, version = _extract_model_metadata(mock_result)

            assert name == "openai:gpt-4"
            assert version is None

    def test_handles_none_result(self) -> None:
        """Test handling None agent result."""
        from api.v1.chat import _extract_model_metadata

        with patch("api.v1.chat.get_settings") as mock_settings:
            mock_settings.return_value.LLM_PROVIDER = "google"
            mock_settings.return_value.CHAT_MODEL = "gemini-pro"

            name, version = _extract_model_metadata(None)

            assert name == "google:gemini-pro"
            assert version is None


class TestGetUserFriendlyErrorMessage:
    """Tests for _get_user_friendly_error_message."""

    def test_handles_503_overloaded(self) -> None:
        """Test handling 503 service unavailable errors."""
        from api.v1.chat import _get_user_friendly_error_message

        result = _get_user_friendly_error_message(Exception("503 Service Unavailable"))

        assert "high demand" in result

    def test_handles_overloaded_keyword(self) -> None:
        """Test handling overloaded keyword in error."""
        from api.v1.chat import _get_user_friendly_error_message

        result = _get_user_friendly_error_message(Exception("Model is overloaded"))

        assert "high demand" in result

    def test_handles_rate_limit(self) -> None:
        """Test handling rate limit errors."""
        from api.v1.chat import _get_user_friendly_error_message

        result = _get_user_friendly_error_message(Exception("429 Rate limit exceeded"))

        assert "too many requests" in result

    def test_handles_quota_exceeded(self) -> None:
        """Test handling quota exceeded errors."""
        from api.v1.chat import _get_user_friendly_error_message

        result = _get_user_friendly_error_message(Exception("Quota exceeded"))

        assert "too many requests" in result

    def test_handles_timeout(self) -> None:
        """Test handling timeout errors."""
        from api.v1.chat import _get_user_friendly_error_message

        result = _get_user_friendly_error_message(Exception("Request timed out"))

        assert "took too long" in result

    def test_handles_model_behavior_error(self) -> None:
        """Test handling unexpected model behavior."""
        from api.v1.chat import _get_user_friendly_error_message

        result = _get_user_friendly_error_message(
            Exception("UnexpectedModelBehavior: output validation failed")
        )

        assert "trouble generating" in result

    def test_handles_connection_error(self) -> None:
        """Test handling connection errors."""
        from api.v1.chat import _get_user_friendly_error_message

        result = _get_user_friendly_error_message(Exception("Connection refused"))

        assert "network issue" in result

    def test_handles_unknown_error(self) -> None:
        """Test handling unknown errors."""
        from api.v1.chat import _get_user_friendly_error_message

        result = _get_user_friendly_error_message(Exception("Something weird happened"))

        assert "Something went wrong" in result
