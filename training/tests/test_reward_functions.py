"""Tests for GRPO reward functions.

Validates that the reward scoring system produces diverse, non-degenerate
scores across different completion qualities — the key property needed for
effective GRPO training (non-zero advantages within groups).

Run from repository root:
    cd apps/backend && PYTHONPATH=../../training/scripts uv run pytest \
        ../../training/tests/test_reward_functions.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure reward_functions module is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from reward_functions import ToolCallRewardComputer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reward() -> ToolCallRewardComputer:
    """Default reward computer with standard weights."""
    return ToolCallRewardComputer()


# ---------------------------------------------------------------------------
# Completion template helpers
# ---------------------------------------------------------------------------


def _tagged(name: str, args: dict | None = None) -> str:
    """Build a properly tagged tool call completion."""
    import json

    args = args or {}
    return f'<tool_call>\n{{"name": "{name}", "arguments": {json.dumps(args)}}}\n</tool_call>'


def _raw_json(name: str, args: dict | None = None) -> str:
    """Build a raw JSON tool call (no tags)."""
    import json

    args = args or {}
    return f'{{"name": "{name}", "arguments": {json.dumps(args)}}}'


def _tagged_with_preamble(name: str, args: dict | None = None) -> str:
    """Build a tagged tool call with explanatory text before it."""
    return f"I'll search for recipes matching your request.\n\n{_tagged(name, args)}"


# ---------------------------------------------------------------------------
# reward_json_validity — continuous scoring
# ---------------------------------------------------------------------------


class TestRewardJsonValidity:
    """Verify JSON validity scoring produces diverse values."""

    def test_no_json_returns_zero(self, reward: ToolCallRewardComputer) -> None:
        assert reward.reward_json_validity("Hello, I can help with cooking!") == 0.0

    def test_attempted_json_returns_partial(
        self, reward: ToolCallRewardComputer
    ) -> None:
        # Has JSON-like structure with "name" but unparseable
        score = reward.reward_json_validity('{"name": "search_recipes", bad json}')
        assert score == 0.15

    def test_raw_json_lower_than_tagged(self, reward: ToolCallRewardComputer) -> None:
        raw = reward.reward_json_validity(
            _raw_json("search_recipes", {"query": "basil"})
        )
        tagged = reward.reward_json_validity(
            _tagged("search_recipes", {"query": "basil"})
        )
        assert tagged > raw, f"Tagged ({tagged}) should score higher than raw ({raw})"

    def test_preamble_lowers_score(self, reward: ToolCallRewardComputer) -> None:
        clean = reward.reward_json_validity(
            _tagged("search_recipes", {"query": "basil"})
        )
        wordy = reward.reward_json_validity(
            _tagged_with_preamble("search_recipes", {"query": "basil"})
        )
        assert clean > wordy, (
            f"Clean ({clean}) should score higher than wordy ({wordy})"
        )

    def test_produces_at_least_four_distinct_values(
        self, reward: ToolCallRewardComputer
    ) -> None:
        """Key GRPO property: diverse scores across quality levels."""
        completions = [
            "Hello, I can help!",  # No JSON
            '{"name": "search_recipes", broken}',  # Attempted
            _raw_json("search_recipes", {"query": "basil"}),  # Raw JSON
            _tagged_with_preamble("search_recipes", {"query": "basil"}),
            _tagged("search_recipes", {"query": "basil"}),  # Perfect
        ]
        scores = [reward.reward_json_validity(c) for c in completions]
        unique = set(scores)
        assert len(unique) >= 4, (
            f"Expected >=4 distinct JSON scores, got {len(unique)}: {scores}"
        )


# ---------------------------------------------------------------------------
# reward_tool_name — correct tool selection
# ---------------------------------------------------------------------------


class TestRewardToolName:
    def test_correct_tool(self, reward: ToolCallRewardComputer) -> None:
        score = reward.reward_tool_name(
            _tagged("search_recipes", {"query": "basil"}), "search_recipes"
        )
        assert score == 1.0

    def test_valid_but_wrong_tool(self, reward: ToolCallRewardComputer) -> None:
        score = reward.reward_tool_name(
            _tagged("web_search", {"query": "basil"}), "search_recipes"
        )
        assert score == 0.5

    def test_invalid_tool(self, reward: ToolCallRewardComputer) -> None:
        score = reward.reward_tool_name(
            _tagged("nonexistent_tool", {}), "search_recipes"
        )
        assert score == 0.0

    def test_no_tool_call(self, reward: ToolCallRewardComputer) -> None:
        score = reward.reward_tool_name("Just some text", "search_recipes")
        assert score == 0.0


# ---------------------------------------------------------------------------
# reward_argument_completeness — required + optional args
# ---------------------------------------------------------------------------


class TestRewardArgumentCompleteness:
    def test_tool_with_no_args_no_optional_perfect(
        self, reward: ToolCallRewardComputer
    ) -> None:
        """get_daily_weather has no required or optional args → 1.0."""
        score = reward.reward_argument_completeness(_tagged("get_daily_weather"))
        assert score == 1.0

    def test_search_with_query_higher_than_without(
        self, reward: ToolCallRewardComputer
    ) -> None:
        """search_recipes has no required args but optional args matter."""
        no_args = reward.reward_argument_completeness(_tagged("search_recipes", {}))
        with_query = reward.reward_argument_completeness(
            _tagged("search_recipes", {"query": "basil"})
        )
        assert with_query > no_args, (
            f"With query ({with_query}) should score higher than none ({no_args})"
        )

    def test_search_more_optional_args_higher(
        self, reward: ToolCallRewardComputer
    ) -> None:
        """More optional args → higher score for search_recipes."""
        one_arg = reward.reward_argument_completeness(
            _tagged("search_recipes", {"query": "basil"})
        )
        multi_args = reward.reward_argument_completeness(
            _tagged("search_recipes", {"query": "basil", "cuisine": "italian"})
        )
        assert multi_args > one_arg

    def test_required_args_partial(self, reward: ToolCallRewardComputer) -> None:
        """update_user_memory requires memory_content."""
        missing = reward.reward_argument_completeness(_tagged("update_user_memory", {}))
        present = reward.reward_argument_completeness(
            _tagged("update_user_memory", {"memory_content": "likes spicy food"})
        )
        assert present > missing
        assert missing < 0.5  # Missing required arg penalized

    def test_search_no_args_returns_0_4(self, reward: ToolCallRewardComputer) -> None:
        """Calling search_recipes with empty args → 0.4 (not 1.0)."""
        score = reward.reward_argument_completeness(_tagged("search_recipes", {}))
        assert score == 0.4

    def test_invalid_tool_returns_zero(self, reward: ToolCallRewardComputer) -> None:
        score = reward.reward_argument_completeness(
            _tagged("fake_tool", {"arg": "val"})
        )
        assert score == 0.0


# ---------------------------------------------------------------------------
# reward_query_expansion — keyword coverage
# ---------------------------------------------------------------------------


class TestRewardQueryExpansion:
    def test_no_tool_call_returns_na(self, reward: ToolCallRewardComputer) -> None:
        score = reward.reward_query_expansion("Hello!", "basil")
        assert score == 0.5

    def test_empty_query_returns_zero(self, reward: ToolCallRewardComputer) -> None:
        score = reward.reward_query_expansion(
            _tagged("search_recipes", {"query": ""}), "basil"
        )
        assert score == 0.0

    def test_keyword_coverage_increases_score(
        self, reward: ToolCallRewardComputer
    ) -> None:
        """More expected keywords matched → higher score."""
        keywords = ["pesto", "preservation", "freeze"]

        zero_match = reward.reward_query_expansion(
            _tagged("search_recipes", {"query": "basil"}),
            "basil",
            expected_keywords=keywords,
        )
        one_match = reward.reward_query_expansion(
            _tagged("search_recipes", {"query": "basil pesto"}),
            "basil",
            expected_keywords=keywords,
        )
        two_match = reward.reward_query_expansion(
            _tagged("search_recipes", {"query": "basil pesto preservation"}),
            "basil",
            expected_keywords=keywords,
        )
        all_match = reward.reward_query_expansion(
            _tagged(
                "search_recipes",
                {"query": "basil pesto preservation freeze"},
            ),
            "basil",
            expected_keywords=keywords,
        )

        assert zero_match < one_match < two_match < all_match, (
            f"Expected monotonic increase: {zero_match}, {one_match}, "
            f"{two_match}, {all_match}"
        )

    def test_or_expansion_bonus(self, reward: ToolCallRewardComputer) -> None:
        without_or = reward.reward_query_expansion(
            _tagged("search_recipes", {"query": "basil pesto"}),
            "basil",
        )
        with_or = reward.reward_query_expansion(
            _tagged("search_recipes", {"query": "basil OR pesto"}),
            "basil",
        )
        assert with_or > without_or

    def test_specificity_keyword_bonus(self, reward: ToolCallRewardComputer) -> None:
        without = reward.reward_query_expansion(
            _tagged("search_recipes", {"query": "basil"}),
            "basil",
        )
        with_specificity = reward.reward_query_expansion(
            _tagged("search_recipes", {"query": "basil recipe ideas"}),
            "basil",
        )
        assert with_specificity > without

    def test_longer_query_bonus(self, reward: ToolCallRewardComputer) -> None:
        short = reward.reward_query_expansion(
            _tagged("search_recipes", {"query": "basil"}),
            "basil",
        )
        long = reward.reward_query_expansion(
            _tagged(
                "search_recipes",
                {"query": "fresh basil pesto pasta dinner"},
            ),
            "basil",
        )
        assert long > short

    def test_produces_many_distinct_values(
        self, reward: ToolCallRewardComputer
    ) -> None:
        """Key GRPO property: keyword matching creates high variance."""
        keywords = ["pesto", "preservation", "freeze"]
        queries = [
            "basil",
            "basil pesto",
            "basil preservation",
            "basil pesto preservation",
            "basil pesto preservation freeze",
            "basil recipe ideas",
            "basil OR pesto OR preservation",
            "basil pesto preservation freeze recipe ideas",
        ]
        scores = [
            reward.reward_query_expansion(
                _tagged("search_recipes", {"query": q}),
                "basil",
                expected_keywords=keywords,
            )
            for q in queries
        ]
        unique = set(scores)
        assert len(unique) >= 5, (
            f"Expected >=5 distinct query scores, got {len(unique)}: "
            f"{list(zip(queries, scores))}"
        )


# ---------------------------------------------------------------------------
# reward_no_tool — continuous response quality
# ---------------------------------------------------------------------------


class TestRewardNoTool:
    def test_expected_tool_set_returns_na(self, reward: ToolCallRewardComputer) -> None:
        score = reward.reward_no_tool("Hello!", "search_recipes")
        assert score == 0.5

    def test_incorrectly_called_tool(self, reward: ToolCallRewardComputer) -> None:
        score = reward.reward_no_tool(
            _tagged("search_recipes", {"query": "basil"}), None
        )
        assert score == 0.0

    def test_empty_response_lower_than_substantive(
        self, reward: ToolCallRewardComputer
    ) -> None:
        empty = reward.reward_no_tool("", None)
        short = reward.reward_no_tool("Sure, I can help!", None)
        long = reward.reward_no_tool(
            "That's a great question! Basil is a wonderful herb. "
            "You can use it in pesto, salads, and many Italian dishes. "
            "It pairs well with tomatoes and mozzarella.",
            None,
        )
        assert empty < short < long

    def test_very_long_response_diminishes(
        self, reward: ToolCallRewardComputer
    ) -> None:
        moderate = reward.reward_no_tool("A " * 100, None)  # 200 chars
        very_long = reward.reward_no_tool("A " * 500, None)  # 1000 chars
        assert very_long <= moderate


# ---------------------------------------------------------------------------
# compute_total_reward — end-to-end scoring
# ---------------------------------------------------------------------------


class TestComputeTotalReward:
    def test_no_tool_correct_varies_by_length(
        self, reward: ToolCallRewardComputer
    ) -> None:
        """No-tool prompts should produce diverse scores, not fixed 1.0."""
        short = reward.compute_total_reward(
            completion="Hi!",
            prompt="Hello",
            expected_tool=None,
        )
        medium = reward.compute_total_reward(
            completion="Hi there! I'm Nibble, your meal planning assistant. "
            "How can I help you today?",
            prompt="Hello",
            expected_tool=None,
        )
        assert short != medium, "No-tool scores should vary (not both 1.0)"

    def test_no_tool_incorrect_tool_call_penalized(
        self, reward: ToolCallRewardComputer
    ) -> None:
        score = reward.compute_total_reward(
            completion=_tagged("search_recipes", {"query": "basil"}),
            prompt="Hello",
            expected_tool=None,
        )
        assert score < 0.2, f"Incorrect tool call should be heavily penalized: {score}"

    def test_keyword_matching_differentiates_search_completions(
        self, reward: ToolCallRewardComputer
    ) -> None:
        """The primary GRPO fix: different keyword coverage → different scores."""
        keywords = ["pesto", "preservation", "freeze"]

        generic = reward.compute_total_reward(
            completion=_tagged("search_recipes", {"query": "basil"}),
            prompt="I have too much basil",
            expected_tool="search_recipes",
            expected_query_keywords=keywords,
        )
        specific = reward.compute_total_reward(
            completion=_tagged(
                "search_recipes",
                {"query": "basil pesto preservation freeze"},
            ),
            prompt="I have too much basil",
            expected_tool="search_recipes",
            expected_query_keywords=keywords,
        )
        assert specific > generic, (
            f"Specific query ({specific}) should score higher than generic ({generic})"
        )

    def test_wrong_tool_vs_right_tool(self, reward: ToolCallRewardComputer) -> None:
        wrong = reward.compute_total_reward(
            completion=_tagged("web_search", {"query": "basil"}),
            prompt="I have too much basil",
            expected_tool="search_recipes",
        )
        right = reward.compute_total_reward(
            completion=_tagged("search_recipes", {"query": "basil"}),
            prompt="I have too much basil",
            expected_tool="search_recipes",
        )
        assert right > wrong

    def test_no_tool_call_when_expected_low(
        self, reward: ToolCallRewardComputer
    ) -> None:
        score = reward.compute_total_reward(
            completion="I can help you find basil recipes!",
            prompt="I have too much basil",
            expected_tool="search_recipes",
        )
        assert score < 0.3


class TestGRPOVarianceProperty:
    """Verify the key property: completions within a GRPO group produce
    diverse scores (non-zero standard deviation) so advantages are non-zero.
    """

    def test_search_group_has_variance(self, reward: ToolCallRewardComputer) -> None:
        """Simulate a GRPO group of 8 completions for a search prompt.

        Even if all completions call the right tool, they should get
        different scores based on query quality and formatting.
        """
        keywords = ["pesto", "preservation", "freeze"]
        prompt = "I have too much basil"

        completions = [
            _tagged("search_recipes", {"query": "basil"}),
            _tagged("search_recipes", {"query": "basil pesto"}),
            _tagged("search_recipes", {"query": "basil preservation recipes"}),
            _tagged(
                "search_recipes",
                {"query": "basil pesto preservation freeze"},
            ),
            _raw_json("search_recipes", {"query": "basil"}),
            _tagged_with_preamble("search_recipes", {"query": "basil"}),
            _tagged("search_recipes", {}),  # No query arg
            _tagged(
                "search_recipes",
                {"query": "basil OR pesto", "cuisine": "italian"},
            ),
        ]

        scores = [
            reward.compute_total_reward(
                completion=c,
                prompt=prompt,
                expected_tool="search_recipes",
                expected_query_keywords=keywords,
            )
            for c in completions
        ]

        # Must have sufficient variance for GRPO learning
        unique = set(scores)
        assert len(unique) >= 5, (
            f"GRPO group needs >=5 distinct scores from 8 completions, "
            f"got {len(unique)}: {sorted(scores)}"
        )

        # Standard deviation should be non-trivial
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std = variance**0.5
        assert std > 0.02, (
            f"GRPO group needs meaningful std dev, got {std:.4f}: {sorted(scores)}"
        )

    def test_no_tool_group_has_variance(self, reward: ToolCallRewardComputer) -> None:
        """Simulate a GRPO group for a no-tool prompt."""
        prompt = "Thanks for helping!"

        completions = [
            "",
            "You're welcome!",
            "You're welcome! Happy to help with meal planning anytime.",
            "You're welcome! I'm Nibble, your meal planning assistant. "
            "I'm always here to help you find recipes, plan meals, "
            "and create grocery lists. Just ask whenever you need help!",
            _tagged("search_recipes", {"query": "thanks"}),  # Wrong: tool call
            "No problem!",
            "Glad I could help! " * 50,  # Very verbose
            "Sure thing.",
        ]

        scores = [
            reward.compute_total_reward(
                completion=c,
                prompt=prompt,
                expected_tool=None,
            )
            for c in completions
        ]

        unique = set(scores)
        assert len(unique) >= 4, (
            f"No-tool GRPO group needs >=4 distinct scores, "
            f"got {len(unique)}: {sorted(scores)}"
        )

    def test_all_prompt_categories_produce_variance(
        self, reward: ToolCallRewardComputer
    ) -> None:
        """Spot-check that reward variance exists for diverse prompt types."""
        import json
        from pathlib import Path

        prompts_path = Path(__file__).parent.parent / "data" / "grpo_prompts.json"
        if not prompts_path.exists():
            pytest.skip("grpo_prompts.json not found")

        with open(prompts_path) as f:
            prompts = json.load(f)

        # Group by category
        categories: dict[str, list[dict]] = {}
        for p in prompts:
            cat = p.get("category", "unknown")
            categories.setdefault(cat, []).append(p)

        # For each category, generate synthetic completions and check variance
        for category, items in categories.items():
            item = items[0]  # Test with first prompt in category
            expected_tool = item.get("expected_tool")
            keywords = item.get("expected_query_keywords")

            if expected_tool:
                completions = [
                    _tagged(expected_tool, {"query": "test"}),
                    _tagged(expected_tool, {}),
                    _raw_json(expected_tool, {"query": "test"}),
                    _tagged_with_preamble(expected_tool, {"query": "test"}),
                ]
            else:
                completions = [
                    "Sure!",
                    "I can help with that. " * 5,
                    "",
                    _tagged("search_recipes", {}),  # Incorrect
                ]

            scores = [
                reward.compute_total_reward(
                    completion=c,
                    prompt=item["prompt"],
                    expected_tool=expected_tool,
                    expected_query_keywords=keywords,
                )
                for c in completions
            ]

            unique = set(scores)
            assert len(unique) >= 2, (
                f"Category '{category}' needs variance in scores, "
                f"got all-same: {scores}"
            )
