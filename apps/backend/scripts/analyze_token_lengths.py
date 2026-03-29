#!/usr/bin/env python3
"""Analyze token length distribution of training samples."""

import json
from pathlib import Path

import tiktoken


# Use cl100k_base (similar to GPT-4, Qwen uses similar tokenizer)
enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(conv: list[dict]) -> int:
    """Count tokens in a conversation including tool calls and results."""
    total = 0
    for msg in conv:
        # Count the main content/value field
        content = msg.get("content", "") or msg.get("value", "") or ""
        total += len(enc.encode(content))

        # Count tool calls (assistant messages with function calls)
        tool_calls = msg.get("tool_calls", [])
        for tc in tool_calls:
            # Function name
            func = tc.get("function", {})
            total += len(enc.encode(func.get("name", "")))
            # Arguments (often JSON)
            total += len(enc.encode(func.get("arguments", "")))

        # Add overhead for role tokens and structure
        total += 4
    return total


def main():
    # Load training data
    train_path = Path("data/train.jsonl")
    val_path = Path("data/val.jsonl")

    train_lengths = []
    val_lengths = []

    print("Analyzing training data...")
    with open(train_path) as f:
        for line in f:
            sample = json.loads(line)
            conv = sample.get("conversations", [])
            tokens = count_tokens(conv)
            train_lengths.append(tokens)

    print("Analyzing validation data...")
    with open(val_path) as f:
        for line in f:
            sample = json.loads(line)
            conv = sample.get("conversations", [])
            tokens = count_tokens(conv)
            val_lengths.append(tokens)

    all_lengths = train_lengths + val_lengths

    print("\n=== Token Length Distribution ===")
    print(f"Training samples: {len(train_lengths)}")
    print(f"Validation samples: {len(val_lengths)}")
    print(f"Total samples: {len(all_lengths)}")
    print()
    print(f"Min: {min(all_lengths):,}")
    print(f"Max: {max(all_lengths):,}")
    print(f"Mean: {sum(all_lengths) / len(all_lengths):,.0f}")

    # Percentiles
    sorted_lengths = sorted(all_lengths)
    for p in [50, 75, 90, 95, 99]:
        idx = int(len(sorted_lengths) * p / 100)
        print(f"P{p}: {sorted_lengths[idx]:,}")

    print()
    print("=== Distribution by Context Window ===")
    for threshold in [1024, 2048, 4096, 8192, 16384, 32768]:
        count = sum(1 for length in all_lengths if length <= threshold)
        pct = count / len(all_lengths) * 100
        print(f"<= {threshold:,}: {count} ({pct:.1f}%)")

    print()
    print("=== Samples Exceeding Common Context Limits ===")
    for threshold in [2048, 4096, 8192, 16384]:
        exceeds = [length for length in all_lengths if length > threshold]
        if exceeds:
            print(f"> {threshold:,}: {len(exceeds)} samples (max: {max(exceeds):,})")


if __name__ == "__main__":
    main()
