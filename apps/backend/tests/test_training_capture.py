"""Tests for AI training data capture service and feedback endpoint."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from services.chat_agent.training_capture import (
    capture_training_sample,
    update_training_sample_feedback,
)


class MockSession:
    """Lightweight mock async session for unit tests."""

    def __init__(self) -> None:
        self._added_objects: list = []
        self._get_result: object | None = None

    def add(self, obj: object) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()
        self._added_objects.append(obj)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def get(self, model_class: type, pk: uuid.UUID) -> object | None:
        return self._get_result

    def set_get_result(self, obj: object | None) -> None:
        self._get_result = obj


@pytest.fixture
def mock_db() -> MockSession:
    """Create a mock database session."""
    return MockSession()


@pytest.mark.asyncio
async def test_capture_training_sample(mock_db: MockSession) -> None:
    """Verify training sample is captured correctly."""
    conversation_id = uuid.uuid4()
    message_id = uuid.uuid4()
    user_id = uuid.uuid4()

    sample = await capture_training_sample(
        mock_db,
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=user_id,
        raw_prompt='[{"role": "user", "content": "What is for dinner?"}]',
        raw_response="Let me search for dinner recipes.",
        tool_calls={"search_recipes": {"query": "dinner"}},
        model_name="gemini-2.5-flash",
        model_version="2025-01-15",
        temperature=0.7,
        max_tokens=1000,
        prompt_tokens=50,
        completion_tokens=20,
        latency_ms=1500,
    )

    assert sample.id is not None
    assert sample.conversation_id == conversation_id
    assert sample.message_id == message_id
    assert sample.user_id == user_id
    assert sample.model_name == "gemini-2.5-flash"
    assert sample.raw_prompt == '[{"role": "user", "content": "What is for dinner?"}]'
    assert sample.raw_response == "Let me search for dinner recipes."
    assert sample.tool_calls == {"search_recipes": {"query": "dinner"}}
    assert sample.user_feedback is None
    assert sample.is_simulated is False
    assert len(mock_db._added_objects) == 1


@pytest.mark.asyncio
async def test_capture_training_sample_minimal(mock_db: MockSession) -> None:
    """Verify training sample captures with minimal required fields."""
    sample = await capture_training_sample(
        mock_db,
        conversation_id=uuid.uuid4(),
        message_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        raw_prompt="Test prompt",
        raw_response="Test response",
        tool_calls=None,
        model_name="test-model",
    )

    assert sample.id is not None
    assert sample.tool_calls is None
    assert sample.temperature is None
    assert sample.latency_ms is None
    assert sample.is_simulated is False


@pytest.mark.asyncio
async def test_capture_training_sample_simulated(mock_db: MockSession) -> None:
    """Verify is_simulated flag is set correctly for synthetic data."""
    sample = await capture_training_sample(
        mock_db,
        conversation_id=uuid.uuid4(),
        message_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        raw_prompt="Synthetic prompt",
        raw_response="Synthetic response",
        tool_calls=None,
        model_name="test-model",
        is_simulated=True,
    )

    assert sample.is_simulated is True


@pytest.mark.asyncio
async def test_update_training_sample_feedback(mock_db: MockSession) -> None:
    """Verify user feedback updates training sample."""
    sample_id = uuid.uuid4()
    mock_sample = SimpleNamespace(
        id=sample_id,
        user_feedback=None,
    )
    mock_db.set_get_result(mock_sample)

    updated = await update_training_sample_feedback(
        mock_db,
        sample_id=sample_id,
        feedback="positive",
    )

    assert updated is not None
    assert updated.user_feedback == "positive"


@pytest.mark.asyncio
async def test_update_training_sample_feedback_not_found(mock_db: MockSession) -> None:
    """Verify feedback update returns None for non-existent sample."""
    mock_db.set_get_result(None)

    result = await update_training_sample_feedback(
        mock_db,
        sample_id=uuid.uuid4(),
        feedback="positive",
    )

    assert result is None
