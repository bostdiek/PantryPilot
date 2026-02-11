#!/usr/bin/env python3
"""Export AI training samples to ChatML JSONL format for Unsloth.

Usage:
    # Basic export
    uv run python scripts/export_training_data.py --output training_data.jsonl

    # With feedback filter
    uv run python scripts/export_training_data.py --output out.jsonl --feedback positive

    # Recent data only
    uv run python scripts/export_training_data.py --output last_week.jsonl --days 7

    # Train/validation split
    uv run python scripts/export_training_data.py \\
        --output train.jsonl --val-output val.jsonl

    # Custom split ratio and seed
    uv run python scripts/export_training_data.py \\
        --output train.jsonl --val-output val.jsonl \\
        --val-ratio 0.15 --seed 123

    # Date range filtering
    uv run python scripts/export_training_data.py --output out.jsonl \\
        --min-date 2026-01-01 --max-date 2026-02-01

    # User-specific export
    uv run python scripts/export_training_data.py --output out.jsonl \\
        --user-id 550e8400-e29b-41d4-a716-446655440000

    # Full tool outputs for long context training (8K-16K)
    uv run python scripts/export_training_data.py --output out.jsonl --full-tool-outputs
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import select

from dependencies.db import AsyncSessionLocal
from models.ai_training_samples import AITrainingSample


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _sample_to_chatml(sample: AITrainingSample) -> dict:
    """Convert a training sample to ChatML format.

    Includes tool calls in the conversation using the function calling format
    compatible with fine-tuning (OpenAI-style tool_calls).

    The raw_prompt now contains properly structured messages with:
    - system: System prompt
    - user: User messages
    - assistant: Assistant responses (may include tool_calls array)
    - tool: Tool return values with tool_call_id
    """
    try:
        prompt_data = json.loads(sample.raw_prompt)
    except json.JSONDecodeError:
        prompt_data = [{"role": "user", "content": sample.raw_prompt}]

    # Check if the prompt already has a system message
    has_system = any(msg.get("role") == "system" for msg in prompt_data)

    conversations = []

    # Add system message if not already present
    if not has_system:
        conversations.append(
            {
                "from": "system",
                "value": (
                    "You are PantryPilot, an AI assistant that helps families "
                    "plan meals, manage recipes, and create grocery lists."
                ),
            }
        )

    # Add conversation history from prompt
    # The prompt now contains properly grouped messages including tool_calls
    for msg in prompt_data:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls")

        if role == "system":
            conversations.append({"from": "system", "value": content})
        elif role == "user":
            conversations.append({"from": "user", "value": content})
        elif role == "assistant":
            # Assistant messages may have content, tool_calls, or both
            assistant_entry: dict = {"from": "assistant", "value": content or ""}
            if tool_calls:
                assistant_entry["tool_calls"] = tool_calls
            conversations.append(assistant_entry)
        elif role == "tool":
            # Tool return messages
            conversations.append(
                {
                    "from": "tool",
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "value": content,
                }
            )

    return {
        "conversations": conversations,
        "metadata": {
            "sample_id": str(sample.id),
            "model_name": sample.model_name,
            "feedback": sample.user_feedback,
            "is_simulated": sample.is_simulated,
            "has_tool_calls": sample.tool_calls is not None,
        },
    }


def _build_sample_query(
    feedback_filter: Literal["positive", "any", "all"] = "all",
    days_back: int | None = None,
    min_date: datetime | None = None,
    max_date: datetime | None = None,
    include_simulated: bool = True,
    user_id: uuid.UUID | None = None,
):
    """Build SQLAlchemy query with common filters.

    Args:
        feedback_filter: Filter by feedback type
        days_back: Only include samples from last N days (overridden by min_date)
        min_date: Minimum created_at date (inclusive)
        max_date: Maximum created_at date (exclusive)
        include_simulated: Whether to include synthetic data samples
        user_id: Filter to specific user UUID

    Returns:
        SQLAlchemy select statement
    """
    stmt = select(AITrainingSample).order_by(AITrainingSample.created_at)

    # Filter by feedback
    if feedback_filter == "positive":
        stmt = stmt.where(AITrainingSample.user_feedback == "positive")
    elif feedback_filter == "any":
        stmt = stmt.where(AITrainingSample.user_feedback.is_not(None))

    # Filter by date range (min_date/max_date take precedence over days_back)
    if min_date:
        stmt = stmt.where(AITrainingSample.created_at >= min_date)
    elif days_back:
        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        stmt = stmt.where(AITrainingSample.created_at >= cutoff)

    if max_date:
        stmt = stmt.where(AITrainingSample.created_at < max_date)

    # Filter by simulated flag
    if not include_simulated:
        stmt = stmt.where(AITrainingSample.is_simulated.is_(False))

    # Filter by user
    if user_id:
        stmt = stmt.where(AITrainingSample.user_id == user_id)

    return stmt


async def export_to_chatml(
    output_file: str,
    feedback_filter: Literal["positive", "any", "all"] = "all",
    days_back: int | None = None,
    min_date: datetime | None = None,
    max_date: datetime | None = None,
    include_simulated: bool = True,
    user_id: uuid.UUID | None = None,
    full_tool_outputs: bool = False,
) -> int:
    """Export training samples to ChatML JSONL format.

    Args:
        output_file: Path to output .jsonl file
        feedback_filter: Filter by feedback:
            - "positive" = only 👍 samples
            - "any" = samples with any feedback (👍 or 👎)
            - "all" = all samples including those without feedback
        days_back: Only include samples from last N days
        min_date: Minimum created_at date (inclusive)
        max_date: Maximum created_at date (exclusive)
        include_simulated: Whether to include synthetic data samples
        user_id: Filter to specific user UUID
        full_tool_outputs: If True, preserves complete tool responses for
            long context training (8K-16K). Default False uses token-optimized
            outputs. Note: Stored samples already contain full outputs;
            this flag indicates intent for long context experiments.

    Returns:
        Number of samples exported
    """
    if full_tool_outputs:
        logger.info("Full tool outputs mode: preserving complete responses")

    async with AsyncSessionLocal() as db:
        stmt = _build_sample_query(
            feedback_filter=feedback_filter,
            days_back=days_back,
            min_date=min_date,
            max_date=max_date,
            include_simulated=include_simulated,
            user_id=user_id,
        )
        result = await db.execute(stmt)
        samples = result.scalars().all()

        # Export to ChatML JSONL format
        count = 0
        with open(output_file, "w") as f:
            for sample in samples:
                chatml_record = _sample_to_chatml(sample)
                # Add metadata flag for long context experiments
                if full_tool_outputs:
                    chatml_record["metadata"]["full_tool_outputs"] = True
                f.write(json.dumps(chatml_record) + "\n")
                count += 1

        return count


async def export_with_split(
    train_file: str,
    val_file: str,
    val_ratio: float = 0.1,
    feedback_filter: Literal["positive", "any", "all"] = "all",
    days_back: int | None = None,
    min_date: datetime | None = None,
    max_date: datetime | None = None,
    include_simulated: bool = True,
    user_id: uuid.UUID | None = None,
    full_tool_outputs: bool = False,
    seed: int = 42,
) -> tuple[int, int]:
    """Export training samples with train/validation split.

    Args:
        train_file: Output path for training data
        val_file: Output path for validation data
        val_ratio: Fraction for validation (default 0.1 = 10%)
        feedback_filter: Filter by feedback type
        days_back: Only include samples from last N days
        min_date: Minimum created_at date (inclusive)
        max_date: Maximum created_at date (exclusive)
        include_simulated: Whether to include synthetic data samples
        user_id: Filter to specific user UUID
        full_tool_outputs: Preserve complete tool responses for long context
        seed: Random seed for reproducible splits

    Returns:
        Tuple of (train_count, val_count)
    """
    if full_tool_outputs:
        logger.info("Full tool outputs mode: preserving complete responses")

    async with AsyncSessionLocal() as db:
        stmt = _build_sample_query(
            feedback_filter=feedback_filter,
            days_back=days_back,
            min_date=min_date,
            max_date=max_date,
            include_simulated=include_simulated,
            user_id=user_id,
        )
        result = await db.execute(stmt)
        samples = list(result.scalars().all())

    if not samples:
        logger.warning("No samples found matching criteria")
        return 0, 0

    # Shuffle with seed for reproducibility
    random.seed(seed)
    random.shuffle(samples)

    # Split
    split_idx = int(len(samples) * (1 - val_ratio))
    train_samples = samples[:split_idx]
    val_samples = samples[split_idx:]

    # Export train
    with open(train_file, "w") as f:
        for sample in train_samples:
            record = _sample_to_chatml(sample)
            if full_tool_outputs:
                record["metadata"]["full_tool_outputs"] = True
            f.write(json.dumps(record) + "\n")

    # Export val
    with open(val_file, "w") as f:
        for sample in val_samples:
            record = _sample_to_chatml(sample)
            if full_tool_outputs:
                record["metadata"]["full_tool_outputs"] = True
            f.write(json.dumps(record) + "\n")

    logger.info(
        "Split %d samples: %d train (%.1f%%), %d val (%.1f%%)",
        len(samples),
        len(train_samples),
        100 * len(train_samples) / len(samples),
        len(val_samples),
        100 * len(val_samples) / len(samples),
    )

    return len(train_samples), len(val_samples)


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse date string to datetime with UTC timezone."""
    if not date_str:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)


def _parse_user_id(user_id_str: str | None) -> uuid.UUID | None:
    """Parse user ID string to UUID, returns None if invalid."""
    if not user_id_str:
        return None
    return uuid.UUID(user_id_str)


def _log_export_config(
    args,
    min_date: datetime | None,
    max_date: datetime | None,
    user_id: uuid.UUID | None,
) -> None:
    """Log export configuration."""
    logger.info("Starting training data export...")
    logger.info("  Output: %s", args.output)
    if args.val_output:
        logger.info("  Validation output: %s", args.val_output)
        logger.info("  Validation ratio: %.1f%%", args.val_ratio * 100)
        logger.info("  Random seed: %d", args.seed)
    logger.info("  Feedback filter: %s", args.feedback)
    if args.days:
        logger.info("  Date range: last %d days", args.days)
    if min_date:
        logger.info("  Min date: %s", min_date.date())
    if max_date:
        logger.info("  Max date: %s", max_date.date())
    if user_id:
        logger.info("  User ID: %s", user_id)
    logger.info("  Include simulated: %s", not args.exclude_simulated)
    if args.full_tool_outputs:
        logger.info("  Full tool outputs: enabled (long context mode)")


def _create_parser() -> argparse.ArgumentParser:
    """Create argument parser for export script."""
    parser = argparse.ArgumentParser(
        description="Export AI training samples to ChatML JSONL format"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output .jsonl file path (train file when using --val-output)",
    )
    parser.add_argument(
        "--val-output",
        help="Output .jsonl file path for validation data (enables train/val split)",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.1,
        help="Fraction of data for validation (default: 0.1)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible splits (default: 42)",
    )
    parser.add_argument(
        "--feedback",
        choices=["positive", "any", "all"],
        default="all",
        help="Filter by user feedback (default: all)",
    )
    parser.add_argument(
        "--days",
        type=int,
        help="Only include samples from last N days",
    )
    parser.add_argument(
        "--min-date",
        type=str,
        help="Minimum date (inclusive), format: YYYY-MM-DD",
    )
    parser.add_argument(
        "--max-date",
        type=str,
        help="Maximum date (exclusive), format: YYYY-MM-DD",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="Filter to specific user UUID",
    )
    parser.add_argument(
        "--exclude-simulated",
        action="store_true",
        help="Exclude synthetic data samples",
    )
    parser.add_argument(
        "--full-tool-outputs",
        action="store_true",
        help="Preserve complete tool responses for long context training (8K-16K)",
    )
    return parser


async def main() -> int:
    """Main entry point for export script."""
    parser = _create_parser()
    args = parser.parse_args()

    # Parse date and user_id arguments
    min_date = _parse_date(args.min_date)
    max_date = _parse_date(args.max_date)

    try:
        user_id = _parse_user_id(args.user_id)
    except ValueError:
        logger.error("Invalid user-id format. Expected UUID.")
        return 1

    _log_export_config(args, min_date, max_date, user_id)

    if args.val_output:
        # Train/validation split mode
        train_count, val_count = await export_with_split(
            train_file=args.output,
            val_file=args.val_output,
            val_ratio=args.val_ratio,
            feedback_filter=args.feedback,
            days_back=args.days,
            min_date=min_date,
            max_date=max_date,
            include_simulated=not args.exclude_simulated,
            user_id=user_id,
            full_tool_outputs=args.full_tool_outputs,
            seed=args.seed,
        )
        logger.info(
            "Exported %d training samples to %s, %d validation samples to %s",
            train_count,
            args.output,
            val_count,
            args.val_output,
        )
    else:
        # Single file mode (legacy behavior)
        count = await export_to_chatml(
            output_file=args.output,
            feedback_filter=args.feedback,
            days_back=args.days,
            min_date=min_date,
            max_date=max_date,
            user_id=user_id,
            full_tool_outputs=args.full_tool_outputs,
        )
        logger.info("Exported %d training samples to %s", count, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
