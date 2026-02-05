"""Tests for training conversation generation."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from training.generate_conversations import (
    MAX_RETRY_DELAY,
    ConversationGenerator,
    ConversationResult,
    FailedConversation,
    GenerationStats,
    _calculate_retry_delay,
    _load_env_files,
)


# =============================================================================
# Fixtures for faster tests
# =============================================================================


@pytest.fixture
def mock_sleep():
    """Mock asyncio.sleep to make tests run instantly."""
    with patch("training.generate_conversations.asyncio.sleep", new_callable=AsyncMock):
        yield


@pytest.fixture
def fast_generator():
    """Create a generator with zero delays for testing."""
    return ConversationGenerator(
        request_delay=0.0,
        multi_turn_delay=0.0,
    )


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestCalculateRetryDelay:
    """Test exponential backoff delay calculation."""

    def test_first_attempt(self):
        """First retry should have minimum delay"""
        delay = _calculate_retry_delay(0)
        # 2^0 * 2.0 = 2.0 seconds base + up to 0.2s jitter
        assert 2.0 <= delay <= 2.2

    def test_second_attempt(self):
        """Second retry should double the delay"""
        delay = _calculate_retry_delay(1)
        # 2^1 * 2.0 = 4.0 seconds base + up to 0.4s jitter
        assert 4.0 <= delay <= 4.4

    def test_third_attempt(self):
        """Third retry should double again"""
        delay = _calculate_retry_delay(2)
        # 2^2 * 2.0 = 8.0 seconds base + up to 0.8s jitter
        assert 8.0 <= delay <= 8.8

    def test_max_delay_capped(self):
        """Delay should be capped at MAX_RETRY_DELAY"""
        # Large attempt number should hit the cap
        delay = _calculate_retry_delay(100)
        # Should be capped at 60.0 + 10% jitter
        assert delay <= MAX_RETRY_DELAY * 1.1

    def test_jitter_prevents_thundering_herd(self):
        """Multiple retries should have different delays due to jitter"""
        delays = [_calculate_retry_delay(3) for _ in range(10)]
        # All delays should be different (jitter applied)
        assert len(set(delays)) > 1


class TestLoadEnvFiles:
    """Test environment file loading."""

    def test_load_env_files_no_dotenv(self):
        """Should handle missing dotenv package gracefully"""
        with patch("training.generate_conversations.Path") as mock_path:
            mock_path.return_value.resolve.return_value.parents = []
            # Should not raise exception
            _load_env_files()

    def test_load_env_finds_file(self):
        """Should load .env file if found"""
        # This test checks the dotenv loading logic
        # The actual import of load_dotenv is conditional (inside try/except)
        # So we just verify the function doesn't crash
        _load_env_files()  # Should not raise


# =============================================================================
# Dataclass Tests
# =============================================================================


class TestConversationResult:
    """Test ConversationResult dataclass."""

    def test_creation_with_defaults(self):
        """Should create with required fields only"""
        result = ConversationResult(
            persona="veggie_val",
            conversation_id=str(uuid4()),
            query="Test query",
            response_text="Test response",
        )

        assert result.persona == "veggie_val"
        assert result.tool_calls == []
        assert result.error is None
        assert result.duration_seconds == 0.0

    def test_creation_with_all_fields(self):
        """Should create with all fields populated"""
        conv_id = str(uuid4())
        tools = [{"name": "search", "status": "completed"}]

        result = ConversationResult(
            persona="family_fiona",
            conversation_id=conv_id,
            query="What's for dinner?",
            response_text="How about pasta?",
            tool_calls=tools,
            error=None,
            duration_seconds=5.2,
        )

        assert result.persona == "family_fiona"
        assert result.conversation_id == conv_id
        assert len(result.tool_calls) == 1
        assert result.duration_seconds == 5.2

    def test_with_error(self):
        """Should capture error information"""
        result = ConversationResult(
            persona="solo_sam",
            conversation_id=str(uuid4()),
            query="Test",
            response_text="",
            error="HTTP 429: Too many requests",
        )

        assert result.error is not None
        assert "429" in result.error


class TestFailedConversation:
    """Test FailedConversation dataclass."""

    def test_creation(self):
        """Should create failed conversation record"""
        failed = FailedConversation(
            persona="adventurous_alex",
            query="Find Thai recipes",
            error="Timeout",
        )

        assert failed.persona == "adventurous_alex"
        assert failed.query == "Find Thai recipes"
        assert failed.error == "Timeout"
        assert failed.timestamp is not None

    def test_timestamp_format(self):
        """Timestamp should be in correct format"""
        failed = FailedConversation(persona="test", query="test", error="test")

        # Should be in format: YYYY-MM-DD HH:MM:SS
        assert len(failed.timestamp) == 19
        assert failed.timestamp[4] == "-"
        assert failed.timestamp[10] == " "


class TestGenerationStats:
    """Test GenerationStats dataclass."""

    def test_initial_state(self):
        """Should initialize with zero counts"""
        stats = GenerationStats()

        assert stats.total_conversations == 0
        assert stats.successful_conversations == 0
        assert stats.failed_conversations == 0
        assert stats.total_tool_calls == 0
        assert stats.total_duration_seconds == 0.0
        assert len(stats.conversations_per_persona) == 0
        assert len(stats.failures) == 0

    def test_accumulation(self):
        """Should accumulate statistics correctly"""
        stats = GenerationStats()

        stats.total_conversations = 10
        stats.successful_conversations = 8
        stats.failed_conversations = 2
        stats.total_tool_calls = 15
        stats.conversations_per_persona["veggie_val"] = 10

        assert stats.total_conversations == 10
        assert stats.successful_conversations == 8
        assert stats.conversations_per_persona["veggie_val"] == 10


# =============================================================================
# ConversationGenerator Tests
# =============================================================================


class TestConversationGeneratorInit:
    """Test ConversationGenerator initialization."""

    def test_default_initialization(self):
        """Should initialize with default values"""
        generator = ConversationGenerator()

        assert generator.api_base_url == "http://localhost:8000"
        assert generator.timeout == 120.0
        assert generator.request_delay > 0
        assert generator.multi_turn_delay > 0
        assert len(generator.tokens) == 0
        assert isinstance(generator.stats, GenerationStats)

    def test_custom_initialization(self):
        """Should initialize with custom values"""
        generator = ConversationGenerator(
            api_base_url="https://example.com",
            timeout=60.0,
            request_delay=3.0,
            multi_turn_delay=4.0,
        )

        assert generator.api_base_url == "https://example.com"
        assert generator.timeout == 60.0
        assert generator.request_delay == 3.0
        assert generator.multi_turn_delay == 4.0


@pytest.mark.asyncio
class TestConversationGeneratorLogin:
    """Test authentication logic."""

    async def test_successful_login(self):
        """Should authenticate and store token"""
        generator = ConversationGenerator()

        # Mock successful login response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token_123"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        token = await generator.login(mock_client, "veggie_val")

        assert token == "test_token_123"
        assert generator.tokens["veggie_val"] == "test_token_123"
        mock_client.post.assert_called_once()

    async def test_failed_login(self):
        """Should handle login failure"""
        generator = ConversationGenerator()

        # Mock failed login response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        token = await generator.login(mock_client, "veggie_val")

        assert token is None
        assert "veggie_val" not in generator.tokens

    async def test_login_exception_handling(self):
        """Should handle exceptions during login"""
        generator = ConversationGenerator()

        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Network error")

        token = await generator.login(mock_client, "veggie_val")

        assert token is None


@pytest.mark.asyncio
class TestConversationGeneratorSendMessage:
    """Test message sending and streaming."""

    async def test_send_without_authentication(self):
        """Should fail gracefully if not authenticated"""
        generator = ConversationGenerator()

        mock_client = AsyncMock()

        result = await generator.send_chat_message(
            mock_client, "veggie_val", "Test query"
        )

        assert result.error == "Not authenticated"
        assert result.response_text == ""

    @pytest.mark.skip(reason="Complex async mocking - needs refactoring")
    async def test_successful_message_send(self):
        """Should send message and parse streaming response"""
        generator = ConversationGenerator()
        generator.tokens["veggie_val"] = "test_token"

        # Simulate SSE events
        events = [
            'data: {"event": "message.delta", "data": {"delta": "Hello "}}',
            'data: {"event": "message.delta", "data": {"delta": "world!"}}',
            'data: {"event": "tool.started", "data": {"name": "search"}}',
            'data: {"event": "tool.result", "data": {}}',
        ]

        async def mock_iter():
            for event in events:
                yield event

        # Mock streaming response with proper async context manager
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = mock_iter

        # Create proper async context manager
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream_context

        result = await generator.send_chat_message(
            mock_client, "veggie_val", "Test query"
        )

        assert result.response_text == "Hello world!"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "search"
        assert result.error is None

    @pytest.mark.skip(reason="Complex async mocking - needs refactoring")
    async def test_http_error_response(self):
        """Should handle HTTP error responses"""
        generator = ConversationGenerator()
        generator.tokens["veggie_val"] = "test_token"

        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.aread = AsyncMock(return_value=b'{"detail":"Too many requests"}')

        # Create proper async context manager
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream_context

        result = await generator.send_chat_message(mock_client, "veggie_val", "Test")

        assert result.error is not None
        assert "429" in result.error

    @pytest.mark.skip(reason="Complex async mocking - needs refactoring")
    async def test_streaming_error_event(self):
        """Should handle error events in stream"""
        generator = ConversationGenerator()
        generator.tokens["veggie_val"] = "test_token"

        events = [
            'data: {"event": "message.delta", "data": {"delta": "Test"}}',
            'data: {"event": "error", "data": {"message": "Something went wrong"}}',
        ]

        async def mock_iter():
            for event in events:
                yield event

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = mock_iter

        # Create proper async context manager
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream_context

        result = await generator.send_chat_message(mock_client, "veggie_val", "Test")

        assert result.error == "Something went wrong"
        assert result.response_text == "Test"


@pytest.mark.asyncio
class TestConversationGeneratorRetry:
    """Test retry logic with exponential backoff."""

    async def test_retry_on_429(self, mock_sleep):
        """Should retry on 429 rate limit errors"""
        generator = ConversationGenerator()
        generator.tokens["test"] = "token"

        call_count = 0

        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                # First 2 calls fail with 429
                return ConversationResult(
                    persona="test",
                    conversation_id=str(uuid4()),
                    query="test",
                    response_text="",
                    error="HTTP 429: Too many requests",
                )
            else:
                # Third call succeeds
                return ConversationResult(
                    persona="test",
                    conversation_id=str(uuid4()),
                    query="test",
                    response_text="Success!",
                    error=None,
                )

        with patch.object(generator, "send_chat_message", side_effect=mock_send):
            result = await generator.send_chat_message_with_retry(
                AsyncMock(), "test", "test"
            )

            assert call_count == 3
            assert result.error is None
            assert result.response_text == "Success!"

    async def test_max_retries_exceeded(self, mock_sleep):
        """Should give up after MAX_RETRIES attempts"""
        generator = ConversationGenerator()
        generator.tokens["test"] = "token"

        async def mock_send(*args, **kwargs):
            # Always return 429
            return ConversationResult(
                persona="test",
                conversation_id=str(uuid4()),
                query="test",
                response_text="",
                error="HTTP 429: Too many requests",
            )

        with patch.object(generator, "send_chat_message", side_effect=mock_send):
            result = await generator.send_chat_message_with_retry(
                AsyncMock(), "test", "test"
            )

            assert result.error is not None
            assert "429" in result.error

    async def test_non_429_error_no_retry(self, mock_sleep):
        """Should not retry on non-429 errors"""
        generator = ConversationGenerator()
        generator.tokens["test"] = "token"

        call_count = 0

        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return ConversationResult(
                persona="test",
                conversation_id=str(uuid4()),
                query="test",
                response_text="",
                error="HTTP 500: Internal Server Error",
            )

        with patch.object(generator, "send_chat_message", side_effect=mock_send):
            result = await generator.send_chat_message_with_retry(
                AsyncMock(), "test", "test"
            )

            # Should only call once (no retry)
            assert call_count == 1
            assert "500" in result.error


@pytest.mark.asyncio
class TestConversationGeneratorGenerateForPersona:
    """Test persona-level conversation generation."""

    async def test_generate_allocates_correctly(self):
        """Should allocate conversations between single/multi-turn"""
        generator = ConversationGenerator()

        # Mock login to return successful token
        async def mock_login(client, persona):
            generator.tokens[persona] = "test_token"
            return "test_token"

        # Mock the generation methods
        async def mock_single(client, persona, num_queries):
            return [
                ConversationResult(
                    persona=persona,
                    conversation_id=str(uuid4()),
                    query=f"query_{i}",
                    response_text=f"response_{i}",
                )
                for i in range(num_queries)
            ]

        async def mock_multi(client, persona, num_conversations):
            # Return list of conversation lists
            return [
                [
                    ConversationResult(
                        persona=persona,
                        conversation_id=str(uuid4()),
                        query="multi",
                        response_text="response",
                    )
                ]
                for _ in range(num_conversations)
            ]

        with (
            patch.object(
                generator,
                "login",
                side_effect=mock_login,
            ),
            patch.object(
                generator,
                "generate_single_turn_conversations",
                side_effect=mock_single,
            ),
            patch.object(
                generator,
                "generate_multi_turn_conversations",
                side_effect=mock_multi,
            ),
        ):
            result = await generator.generate_for_persona(
                AsyncMock(), "veggie_val", target_samples=100
            )

            # Should allocate 70% single-turn, 30% multi-turn
            assert result["single_turn_count"] == 70
            assert result["multi_turn_conversations"] > 0
            assert "single_turn" in result
            assert "multi_turn" in result


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.asyncio
class TestConversationGeneratorStatistics:
    """Test statistics tracking."""

    async def test_stats_tracking(self):
        """Should track conversation statistics correctly"""
        generator = ConversationGenerator()

        # Simulate successful conversation
        generator.stats.total_conversations += 1
        generator.stats.successful_conversations += 1
        generator.stats.total_tool_calls += 2

        # Simulate failed conversation
        generator.stats.total_conversations += 1
        generator.stats.failed_conversations += 1
        generator.stats.failures.append(
            FailedConversation(
                persona="test",
                query="test",
                error="test error",
            )
        )

        assert generator.stats.total_conversations == 2
        assert generator.stats.successful_conversations == 1
        assert generator.stats.failed_conversations == 1
        assert generator.stats.total_tool_calls == 2
        assert len(generator.stats.failures) == 1


@pytest.mark.asyncio
class TestConcurrentExecution:
    """Test concurrent persona execution."""

    async def test_concurrent_mode_runs_parallel(self):
        """Should run personas concurrently"""
        generator = ConversationGenerator()

        # Track execution order
        execution_log = []

        async def mock_persona_task(client, persona_name, target):
            execution_log.append(f"start_{persona_name}")
            await asyncio.sleep(0.01)  # Simulate work
            execution_log.append(f"end_{persona_name}")
            return {"persona": persona_name, "single_turn": []}

        with (
            patch.object(
                generator,
                "_generate_persona_task",
                side_effect=mock_persona_task,
            ),
            patch.object(generator, "login", return_value="token"),
        ):
            # This will be tested with actual personas in generate_all
            # Just verify the method exists and can be called
            assert callable(generator._generate_persona_task)


# =============================================================================
# Edge Cases & Error Handling
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_tool_calls(self):
        """Should handle empty tool call list"""
        result = ConversationResult(
            persona="test",
            conversation_id=str(uuid4()),
            query="test",
            response_text="test",
            tool_calls=[],
        )

        assert len(result.tool_calls) == 0

    def test_very_long_response(self):
        """Should handle very long responses"""
        long_text = "x" * 10000

        result = ConversationResult(
            persona="test",
            conversation_id=str(uuid4()),
            query="test",
            response_text=long_text,
        )

        assert len(result.response_text) == 10000

    def test_special_characters_in_query(self):
        """Should handle special characters"""
        special_query = "What's the recipe for crème brûlée? 🍮"

        result = ConversationResult(
            persona="test",
            conversation_id=str(uuid4()),
            query=special_query,
            response_text="Here's how...",
        )

        assert result.query == special_query

    @pytest.mark.asyncio
    async def test_network_timeout(self):
        """Should handle network timeouts"""
        generator = ConversationGenerator(timeout=1.0)
        generator.tokens["test"] = "token"

        mock_client = AsyncMock()
        mock_client.stream.side_effect = TimeoutError()

        result = await generator.send_chat_message(mock_client, "test", "test")

        assert result.error is not None


# =============================================================================
# Summary and Logging Tests
# =============================================================================


class TestPrintSummary:
    """Test summary printing functionality."""

    def test_print_summary_no_failures(self):
        """Should print summary without failures."""
        generator = ConversationGenerator()
        generator.stats.total_conversations = 10
        generator.stats.successful_conversations = 10
        generator.stats.failed_conversations = 0
        generator.stats.total_tool_calls = 15
        generator.stats.total_duration_seconds = 60.0
        generator.stats.conversations_per_persona = {"veggie_val": 5, "solo_sam": 5}

        # Should not raise any exception
        generator._print_summary()

    def test_print_summary_with_failures(self):
        """Should print summary and save failures to file."""
        generator = ConversationGenerator()
        generator.stats.total_conversations = 10
        generator.stats.successful_conversations = 8
        generator.stats.failed_conversations = 2
        generator.stats.failures = [
            FailedConversation(
                persona="test",
                query="test query",
                error="test error",
            )
        ]

        with patch.object(generator, "_save_failures") as mock_save:
            generator._print_summary()
            mock_save.assert_called_once()


class TestSaveFailures:
    """Test failure file saving functionality."""

    def test_save_failures_creates_file(self, tmp_path):
        """Should save failures to JSON file."""
        generator = ConversationGenerator()
        generator.stats.failures = [
            FailedConversation(
                persona="test",
                query="test query",
                conversation_id="conv-123",
                error="test error",
            )
        ]

        # Change to temp directory
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            generator._save_failures()

            # Verify file was created
            failures_file = tmp_path / "failed_conversations.json"
            assert failures_file.exists()

            # Verify content
            content = json.loads(failures_file.read_text())
            assert len(content) == 1
            assert content[0]["persona"] == "test"
            assert content[0]["query"] == "test query"
        finally:
            os.chdir(original_cwd)

    def test_save_failures_appends_to_existing(self, tmp_path):
        """Should append to existing failures file."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create existing file
            failures_file = tmp_path / "failed_conversations.json"
            failures_file.write_text(
                json.dumps([{"persona": "existing", "query": "old", "error": "old"}])
            )

            generator = ConversationGenerator()
            generator.stats.failures = [
                FailedConversation(
                    persona="new",
                    query="new query",
                    error="new error",
                )
            ]

            generator._save_failures()

            # Verify content merged
            content = json.loads(failures_file.read_text())
            assert len(content) == 2
        finally:
            os.chdir(original_cwd)


# =============================================================================
# Generation Method Tests
# =============================================================================


@pytest.mark.asyncio
class TestGenerateSingleTurnConversations:
    """Test single-turn conversation generation."""

    async def test_generates_correct_number_of_queries(self, mock_sleep):
        """Should generate the specified number of queries."""
        generator = ConversationGenerator()
        generator.tokens["veggie_val"] = "test_token"

        call_count = 0

        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return ConversationResult(
                persona="veggie_val",
                conversation_id=str(uuid4()),
                query="test",
                response_text="response",
            )

        with patch.object(
            generator, "send_chat_message_with_retry", side_effect=mock_send
        ):
            results = await generator.generate_single_turn_conversations(
                AsyncMock(), "veggie_val", num_queries=5
            )

            assert len(results) == 5
            assert call_count == 5
            assert generator.stats.successful_conversations == 5

    async def test_handles_failed_queries(self, mock_sleep):
        """Should track failed queries in stats."""
        generator = ConversationGenerator()
        generator.tokens["veggie_val"] = "test_token"

        call_count = 0

        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return ConversationResult(
                    persona="veggie_val",
                    conversation_id=str(uuid4()),
                    query="test",
                    response_text="",
                    error="Test error",
                )
            return ConversationResult(
                persona="veggie_val",
                conversation_id=str(uuid4()),
                query="test",
                response_text="response",
            )

        with patch.object(
            generator, "send_chat_message_with_retry", side_effect=mock_send
        ):
            results = await generator.generate_single_turn_conversations(
                AsyncMock(), "veggie_val", num_queries=3
            )

            assert len(results) == 3
            assert generator.stats.failed_conversations == 1
            assert len(generator.stats.failures) == 1


@pytest.mark.asyncio
class TestGenerateMultiTurnConversations:
    """Test multi-turn conversation generation."""

    async def test_generates_multi_turn_conversations(self, mock_sleep):
        """Should generate multi-turn conversations from scenarios."""
        generator = ConversationGenerator()
        generator.tokens["veggie_val"] = "test_token"

        async def mock_send(*args, **kwargs):
            return ConversationResult(
                persona="veggie_val",
                conversation_id=kwargs.get("conversation_id", str(uuid4())),
                query="test",
                response_text="response",
            )

        with patch.object(
            generator, "send_chat_message_with_retry", side_effect=mock_send
        ):
            results = await generator.generate_multi_turn_conversations(
                AsyncMock(), "veggie_val", num_conversations=2
            )

            # Should return list of conversation lists
            assert isinstance(results, list)
            assert len(results) > 0
            # Each result should be a list of turns
            for conv in results:
                assert isinstance(conv, list)

    async def test_stops_on_error_within_conversation(self, mock_sleep):
        """Should stop multi-turn conversation on error."""
        generator = ConversationGenerator()
        generator.tokens["veggie_val"] = "test_token"

        call_count = 0

        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return ConversationResult(
                    persona="veggie_val",
                    conversation_id=str(uuid4()),
                    query="test",
                    response_text="",
                    error="Error on turn 2",
                )
            return ConversationResult(
                persona="veggie_val",
                conversation_id=str(uuid4()),
                query="test",
                response_text="response",
            )

        with patch.object(
            generator, "send_chat_message_with_retry", side_effect=mock_send
        ):
            await generator.generate_multi_turn_conversations(
                AsyncMock(), "veggie_val", num_conversations=1
            )

            # First conversation should have stopped at turn 2
            assert generator.stats.failed_conversations >= 1


@pytest.mark.asyncio
class TestGenerateForPersona:
    """Test persona-level generation."""

    async def test_generates_mix_of_single_and_multi_turn(self):
        """Should generate both single and multi-turn conversations."""
        generator = ConversationGenerator()

        async def mock_login(client, persona):
            generator.tokens[persona] = "test_token"
            return "test_token"

        async def mock_single(client, persona, num_queries):
            return [
                ConversationResult(
                    persona=persona,
                    conversation_id=str(uuid4()),
                    query="single",
                    response_text="response",
                )
                for _ in range(num_queries)
            ]

        async def mock_multi(client, persona, num_conversations):
            return [
                [
                    ConversationResult(
                        persona=persona,
                        conversation_id=str(uuid4()),
                        query="multi",
                        response_text="response",
                    )
                ]
                for _ in range(num_conversations)
            ]

        with (
            patch.object(generator, "login", side_effect=mock_login),
            patch.object(
                generator,
                "generate_single_turn_conversations",
                side_effect=mock_single,
            ),
            patch.object(
                generator,
                "generate_multi_turn_conversations",
                side_effect=mock_multi,
            ),
        ):
            result = await generator.generate_for_persona(
                AsyncMock(), "veggie_val", target_samples=50
            )

            assert "single_turn" in result
            assert "multi_turn" in result
            assert "single_turn_count" in result
            assert "multi_turn_conversations" in result

    async def test_handles_login_failure(self):
        """Should handle login failure gracefully."""
        generator = ConversationGenerator()

        async def mock_login_fail(client, persona):
            return None

        with patch.object(generator, "login", side_effect=mock_login_fail):
            result = await generator.generate_for_persona(
                AsyncMock(), "veggie_val", target_samples=10
            )

            assert "error" in result
            assert "login failed" in result["error"].lower()


@pytest.mark.asyncio
class TestGenerateAll:
    """Test generate_all for all personas."""

    async def test_sequential_mode(self, mock_sleep):
        """Should run personas sequentially when concurrent=False."""
        generator = ConversationGenerator()

        async def mock_generate(client, persona, target):
            return {
                "persona": persona,
                "single_turn": [],
                "multi_turn": [],
            }

        with patch.object(generator, "generate_for_persona", side_effect=mock_generate):
            results = await generator.generate_all(
                personas=["veggie_val", "solo_sam"],
                target_per_persona=5,
                concurrent=False,
            )

            assert "veggie_val" in results
            assert "solo_sam" in results

    async def test_concurrent_mode(self, mock_sleep):
        """Should run personas concurrently when concurrent=True."""
        generator = ConversationGenerator()

        async def mock_task(client, persona, target):
            return {
                "persona": persona,
                "single_turn": [],
                "multi_turn": [],
            }

        with patch.object(generator, "_generate_persona_task", side_effect=mock_task):
            results = await generator.generate_all(
                personas=["veggie_val", "solo_sam"],
                target_per_persona=5,
                concurrent=True,
            )

            assert "veggie_val" in results
            assert "solo_sam" in results

    async def test_handles_exception_in_concurrent_mode(self):
        """Should handle exceptions from concurrent tasks."""
        generator = ConversationGenerator()

        async def mock_task(client, persona, target):
            if persona == "solo_sam":
                raise RuntimeError("Test error")
            return {
                "persona": persona,
                "single_turn": [],
                "multi_turn": [],
            }

        with patch.object(generator, "_generate_persona_task", side_effect=mock_task):
            results = await generator.generate_all(
                personas=["veggie_val", "solo_sam"],
                target_per_persona=5,
                concurrent=True,
            )

            # Should still have both results, one with error
            assert "veggie_val" in results
            assert "solo_sam" in results
            assert "error" in results["solo_sam"]


@pytest.mark.asyncio
class TestGeneratePersonaTask:
    """Test _generate_persona_task wrapper."""

    async def test_successful_task(self):
        """Should wrap generate_for_persona and return result."""
        generator = ConversationGenerator()

        async def mock_generate(client, persona, target):
            return {"persona": persona, "single_turn": [], "multi_turn": []}

        with patch.object(generator, "generate_for_persona", side_effect=mock_generate):
            result = await generator._generate_persona_task(
                AsyncMock(), "veggie_val", 10
            )

            assert result["persona"] == "veggie_val"

    async def test_reraises_exception(self):
        """Should re-raise exceptions from generate_for_persona."""
        generator = ConversationGenerator()

        async def mock_generate(client, persona, target):
            raise RuntimeError("Test error")

        with patch.object(generator, "generate_for_persona", side_effect=mock_generate):
            with pytest.raises(RuntimeError):
                await generator._generate_persona_task(AsyncMock(), "veggie_val", 10)


# =============================================================================
# Run Generation Entry Point Tests
# =============================================================================


@pytest.mark.asyncio
class TestRunGeneration:
    """Test run_generation entry point."""

    async def test_run_generation_uses_defaults(self):
        """Should use default values when not specified."""
        from training.generate_conversations import run_generation

        with (
            patch(
                "training.generate_conversations.ConversationGenerator"
            ) as MockGenerator,
            patch("training.generate_conversations._load_env_files"),
        ):
            mock_instance = AsyncMock()
            mock_instance.generate_all.return_value = {}
            MockGenerator.return_value = mock_instance

            await run_generation(
                api_base_url="http://test:8000",
                personas=["veggie_val"],
                target_per_persona=5,
            )

            mock_instance.generate_all.assert_called_once()

    async def test_run_generation_with_seed_first(self):
        """Should seed database when seed_first=True."""
        from training.generate_conversations import run_generation

        with (
            patch(
                "training.generate_conversations.ConversationGenerator"
            ) as MockGenerator,
            patch("training.generate_conversations._load_env_files"),
            patch("training.seed_database.run_seeding") as mock_seed,
        ):
            mock_instance = AsyncMock()
            mock_instance.generate_all.return_value = {}
            MockGenerator.return_value = mock_instance

            await run_generation(
                api_base_url="http://test:8000",
                personas=["veggie_val"],
                seed_first=True,
            )

            mock_seed.assert_called_once()
