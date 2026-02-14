#!/usr/bin/env python3
"""
Reward Functions for GRPO Training of PantryPilot Tool-Calling Agent

Implements multi-signal reward computation for Group Relative Policy
Optimization (GRPO) training. Scores model completions on:
- JSON validity of generated tool calls
- Correct tool selection from available PantryPilot tools
- Argument completeness (required args present)
- Search query quality and expansion

Usage:
    from reward_functions import ToolCallRewardComputer

    reward_computer = ToolCallRewardComputer()
    score = reward_computer.compute_total_reward(
        completion="<tool_call>...",
        prompt="I have too much basil",
        expected_tool="search_recipes",
    )
"""

from __future__ import annotations

import json
import re

# PantryPilot tool definitions aligned with the actual agent tool set
# in apps/backend/src/services/chat_agent/tools/
AVAILABLE_TOOLS: dict[str, dict[str, list[str]]] = {
    "search_recipes": {
        "required_args": [],
        "optional_args": [
            "query",
            "cuisine",
            "difficulty",
            "max_cook_time",
            "min_times_cooked",
            "sort_by",
            "include_full_recipe",
        ],
    },
    "get_meal_plan_history": {
        "required_args": [],
        "optional_args": ["days"],
    },
    "propose_meal_for_day": {
        "required_args": ["date", "day_label"],
        "optional_args": [
            "existing_recipe_id",
            "existing_recipe_title",
            "existing_recipe_image_url",
            "existing_recipe_detail_path",
            "new_recipe_title",
            "new_recipe_source_url",
            "new_recipe_description",
            "is_leftover",
            "is_eating_out",
            "notes",
        ],
    },
    "suggest_recipe": {
        "required_args": [
            "title",
            "description",
            "prep_time_minutes",
            "cook_time_minutes",
            "serving_min",
            "instructions",
            "category",
            "ingredients",
        ],
        "optional_args": ["source_url"],
    },
    "update_user_memory": {
        "required_args": ["memory_content"],
        "optional_args": [],
    },
    "get_daily_weather": {
        "required_args": [],
        "optional_args": [],
    },
    "web_search": {
        "required_args": ["query"],
        "optional_args": [],
    },
    "fetch_url_as_markdown": {
        "required_args": ["url"],
        "optional_args": [],
    },
}


class ToolCallRewardComputer:
    """Compute rewards for tool-calling outputs.

    Evaluates model completions on four dimensions:
    1. JSON validity — can the tool call be parsed?
    2. Tool name — is the selected tool correct/valid?
    3. Argument completeness — are required args present?
    4. Query expansion — how well does the search query cover intent?

    Each dimension produces a score in [0, 1] which is combined
    using configurable weights into a total reward.
    """

    def __init__(
        self,
        json_weight: float = 1.0,
        tool_weight: float = 2.0,
        args_weight: float = 1.5,
        query_weight: float = 1.0,
    ) -> None:
        self.json_weight = json_weight
        self.tool_weight = tool_weight
        self.args_weight = args_weight
        self.query_weight = query_weight

    def _extract_tool_call(self, completion: str) -> dict | None:
        """Extract tool call dict from model completion text.

        Handles multiple formats:
        - <tool_call>{"name": ..., "arguments": ...}</tool_call>
        - {"name": ..., "arguments": ...}  (raw JSON)
        - Function call blocks from ChatML

        Returns:
            Parsed tool call dict with 'name' and 'arguments' keys,
            or None if no valid tool call found.
        """
        # Try <tool_call> tags first (ChatML / Qwen style)
        tag_match = re.search(
            r"<tool_call>\s*(\{.*?\})\s*</tool_call>", completion, re.DOTALL
        )
        if tag_match:
            try:
                return json.loads(tag_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try raw JSON with name/arguments structure
        json_match = re.search(
            r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{.*?\}\s*\}',
            completion,
            re.DOTALL,
        )
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Try to find any JSON object in the completion
        for match in re.finditer(r"\{[^{}]*\}", completion):
            try:
                parsed = json.loads(match.group(0))
                if "name" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

        return None

    def reward_json_validity(self, completion: str) -> float:
        """Score JSON parsability: 1.0 (valid) / 0.5 (partial) / 0.0 (invalid)."""
        tool_call = self._extract_tool_call(completion)
        if tool_call is None:
            return 0.0

        try:
            json.loads(json.dumps(tool_call))  # Ensure serializable
            return 1.0
        except (TypeError, ValueError):
            return 0.5

    def reward_tool_name(
        self, completion: str, expected_tool: str | None = None
    ) -> float:
        """Score tool selection.

        Returns: 1.0 (correct) / 0.5 (valid but wrong) / 0.0 (invalid).
        """
        tool_call = self._extract_tool_call(completion)
        if tool_call is None:
            return 0.0

        tool_name = tool_call.get("name", "")

        if expected_tool and tool_name == expected_tool:
            return 1.0
        elif tool_name in AVAILABLE_TOOLS:
            return 0.5
        else:
            return 0.0

    def reward_argument_completeness(self, completion: str) -> float:
        """Score argument presence: ratio of required args present."""
        tool_call = self._extract_tool_call(completion)
        if tool_call is None:
            return 0.0

        tool_name = tool_call.get("name", "")
        args = tool_call.get("arguments", {})

        if tool_name not in AVAILABLE_TOOLS:
            return 0.0

        required = AVAILABLE_TOOLS[tool_name]["required_args"]
        if not required:
            return 1.0

        present = sum(1 for arg in required if arg in args)
        return present / len(required)

    def reward_query_expansion(self, completion: str, context: str) -> float:
        """Score search query quality for query expansion tasks.

        Rewards:
        - OR expansion (e.g., "pesto OR preservation")
        - Specificity (e.g., "basil preservation methods")
        - Context-aware keywords
        """
        tool_call = self._extract_tool_call(completion)
        if tool_call is None or tool_call.get("name") != "search_recipes":
            return 0.5  # N/A — not a search task

        query = tool_call.get("arguments", {}).get("query", "")
        if not query:
            return 0.0

        score = 0.5  # Base score for having a query

        # Reward OR expansion
        if " OR " in query or "|" in query:
            score += 0.2

        # Reward specificity keywords
        specificity_keywords = ["recipe", "method", "technique", "ideas", "ways"]
        if any(kw in query.lower() for kw in specificity_keywords):
            score += 0.15

        # Reward context-aware expansion
        context_terms: dict[str, list[str]] = {
            "extra": ["preservation", "use up", "freeze", "store"],
            "too much": ["bulk", "large batch", "freeze"],
            "leftover": ["repurpose", "next day", "transform"],
            "expiring": ["quick", "urgent", "preserve"],
        }
        for trigger, expected in context_terms.items():
            if trigger in context.lower():
                if any(exp in query.lower() for exp in expected):
                    score += 0.15
                    break

        return min(score, 1.0)

    def reward_no_tool(self, completion: str, expected_tool: str | None) -> float:
        """Score correct non-tool-call behavior.

        When expected_tool is None, the model should NOT produce a tool call.
        Returns 1.0 if no tool call found, 0.0 if one is generated.
        """
        if expected_tool is not None:
            return 0.5  # N/A — not a no-tool scenario

        tool_call = self._extract_tool_call(completion)
        return 1.0 if tool_call is None else 0.0

    def compute_total_reward(
        self,
        completion: str,
        prompt: str,
        expected_tool: str | None = None,
    ) -> float:
        """Compute weighted total reward.

        For prompts where no tool is expected (expected_tool=None),
        uses the no-tool reward instead of tool-specific scores.
        """
        if expected_tool is None:
            # No tool expected — reward model for NOT calling tools
            no_tool_score = self.reward_no_tool(completion, expected_tool)
            json_score = self.reward_json_validity(completion)
            # If no tool call found, that's correct: reward highly
            # If tool call found, penalize
            if no_tool_score == 1.0:
                return 1.0
            else:
                # Model incorrectly called a tool — partial credit for
                # well-formed JSON but penalize for wrong decision
                return json_score * 0.2

        # Tool expected — score all dimensions
        rewards = {
            "json": self.reward_json_validity(completion) * self.json_weight,
            "tool": self.reward_tool_name(completion, expected_tool) * self.tool_weight,
            "args": self.reward_argument_completeness(completion) * self.args_weight,
            "query": self.reward_query_expansion(completion, prompt)
            * self.query_weight,
        }

        total_weight = (
            self.json_weight + self.tool_weight + self.args_weight + self.query_weight
        )
        return sum(rewards.values()) / total_weight
