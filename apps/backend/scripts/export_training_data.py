#!/usr/bin/env python3
"""Export AI training samples to ChatML JSONL format for Unsloth.

Usage:
    uv run python scripts/export_training_data.py --output training_data.jsonl
    uv run python scripts/export_training_data.py --output out.jsonl --feedback positive
    uv run python scripts/export_training_data.py --output last_week.jsonl --days 7
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
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


async def export_to_chatml(
    output_file: str,
    feedback_filter: Literal["positive", "any", "all"] = "all",
    days_back: int | None = None,
    include_simulated: bool = True,
) -> int:
    """Export training samples to ChatML JSONL format.

    Args:
        output_file: Path to output .jsonl file
        feedback_filter: Filter by feedback:
            - "positive" = only 👍 samples
            - "any" = samples with any feedback (👍 or 👎)
            - "all" = all samples including those without feedback
        days_back: Only include samples from last N days
        include_simulated: Whether to include synthetic data samples

    Returns:
        Number of samples exported
    """
    async with AsyncSessionLocal() as db:
        # Build query
        stmt = select(AITrainingSample).order_by(AITrainingSample.created_at)

        # Filter by feedback
        if feedback_filter == "positive":
            stmt = stmt.where(AITrainingSample.user_feedback == "positive")
        elif feedback_filter == "any":
            stmt = stmt.where(AITrainingSample.user_feedback.is_not(None))
        # "all" means no feedback filter

        # Filter by date
        if days_back:
            cutoff = datetime.now(UTC) - timedelta(days=days_back)
            stmt = stmt.where(AITrainingSample.created_at >= cutoff)

        # Filter by simulated flag
        if not include_simulated:
            stmt = stmt.where(AITrainingSample.is_simulated.is_(False))

        result = await db.execute(stmt)
        samples = result.scalars().all()

        # Export to ChatML JSONL format
        count = 0
        with open(output_file, "w") as f:
            for sample in samples:
                chatml_record = _sample_to_chatml(sample)
                f.write(json.dumps(chatml_record) + "\n")
                count += 1

        return count


async def main() -> int:
    """Main entry point for export script."""
    parser = argparse.ArgumentParser(
        description="Export AI training samples to ChatML JSONL format"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output .jsonl file path",
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
        "--exclude-simulated",
        action="store_true",
        help="Exclude synthetic data samples",
    )

    args = parser.parse_args()

    logger.info("Starting training data export...")
    logger.info("  Output: %s", args.output)
    logger.info("  Feedback filter: %s", args.feedback)
    if args.days:
        logger.info("  Date range: last %d days", args.days)
    logger.info("  Include simulated: %s", not args.exclude_simulated)

    count = await export_to_chatml(
        output_file=args.output,
        feedback_filter=args.feedback,
        days_back=args.days,
        include_simulated=not args.exclude_simulated,
    )

    logger.info("Exported %d training samples to %s", count, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
