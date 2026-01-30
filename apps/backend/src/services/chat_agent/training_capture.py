"""Service for capturing LLM interactions as training data."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_training_samples import AITrainingSample


logger = logging.getLogger(__name__)


async def capture_training_sample(
    db: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    raw_prompt: str,
    raw_response: str,
    tool_calls: dict[str, Any] | None,
    model_name: str,
    model_version: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    latency_ms: int | None = None,
    is_simulated: bool = False,
) -> AITrainingSample:
    """Capture LLM interaction for fine-tuning training data.

    Args:
        db: Database session
        conversation_id: Chat conversation ID
        message_id: Assistant message ID
        user_id: User who initiated the request
        raw_prompt: Complete prompt sent to LLM (system + context + user message)
        raw_response: Raw model output before parsing
        tool_calls: List of tool calls made (if any)
        model_name: LLM model identifier
        model_version: Model version/timestamp
        temperature: Sampling temperature
        max_tokens: Max completion tokens
        prompt_tokens: Prompt token count
        completion_tokens: Completion token count
        latency_ms: Total request latency in milliseconds
        is_simulated: True if from synthetic data generation

    Returns:
        Created training sample record
    """
    sample = AITrainingSample(
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=user_id,
        raw_prompt=raw_prompt,
        raw_response=raw_response,
        tool_calls=tool_calls,
        model_name=model_name,
        model_version=model_version,
        temperature=temperature,
        max_tokens=max_tokens,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        is_simulated=is_simulated,
    )

    db.add(sample)
    await db.flush()
    await db.commit()

    logger.debug(
        "Captured training sample %s for conversation %s",
        sample.id,
        conversation_id,
    )

    return sample


async def update_training_sample_feedback(
    db: AsyncSession,
    *,
    sample_id: uuid.UUID,
    feedback: str,
) -> AITrainingSample | None:
    """Update user feedback for a training sample.

    Args:
        db: Database session
        sample_id: Training sample ID
        feedback: User feedback value ("positive" or "negative")

    Returns:
        Updated training sample or None if not found
    """
    sample = await db.get(AITrainingSample, sample_id)
    if sample is None:
        return None

    sample.user_feedback = feedback
    await db.flush()

    logger.debug("Updated feedback for training sample %s: %s", sample_id, feedback)

    return sample
