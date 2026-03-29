#!/usr/bin/env python3
"""
Reward Functions for GRPO Training of PantryPilot Tool-Calling Agent

Implements multi-signal reward computation for Group Relative Policy
Optimization (GRPO) training. Scores model completions on:
- JSON validity of generated tool calls
- Correct tool selection from available PantryPilot tools
- Argument completeness (required args present)
- Search query quality and keyword coverage

Usage:
    from reward_functions import ToolCallRewardComputer

    reward_computer = ToolCallRewardComputer()
    score = reward_computer.compute_total_reward(
        completion="<tool_call>...",
        prompt="I have too much basil",
        expected_tool="search_recipes",
        expected_query_keywords=["pesto", "preservation", "freeze"],
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
    "get_recipe_details": {
        "required_args": ["recipe_id"],
        "optional_args": [],
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
        """Score JSON parsability and format quality on a continuous scale.

        Produces diverse scores by evaluating both parseability and
        formatting quality to differentiate completions within a GRPO group.

        Scoring breakdown:
          - 0.0:  No JSON or tool call structure found
          - 0.15: JSON-like structure attempted but unparseable
          - 0.5:  Valid tool call JSON (base)
          - +0.15: Has both 'name' and 'arguments' keys
          - +0.2:  Proper <tool_call>...</tool_call> tags
          - +0.15: Minimal extraneous text around the tool call

        Returns:
            Float in [0.0, 1.0]
        """
        has_open_tag = "<tool_call>" in completion
        has_close_tag = "</tool_call>" in completion

        tool_call = self._extract_tool_call(completion)
        if tool_call is None:
            # Partial credit for attempting JSON structure
            if "{" in completion and '"name"' in completion:
                return 0.15
            return 0.0

        score = 0.5  # Base: parseable tool call found

        # Structure quality
        if "name" in tool_call and "arguments" in tool_call:
            score += 0.15
        elif "name" in tool_call:
            score += 0.05

        # Tag formatting (ChatML compliance)
        if has_open_tag and has_close_tag:
            score += 0.2
        elif has_open_tag:
            score += 0.1

        # Conciseness: reward minimal text outside the tool call
        if has_open_tag:
            before = completion.split("<tool_call>")[0].strip()
        else:
            before = completion.split("{")[0].strip()
        after = completion.split("</tool_call>")[-1].strip() if has_close_tag else ""
        extra_chars = len(before) + len(after)

        if extra_chars < 10:
            score += 0.15
        elif extra_chars < 50:
            score += 0.08
        elif extra_chars < 100:
            score += 0.03

        return min(score, 1.0)

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
        """Score argument quality: required args + useful optional args.

        For tools with required args: primary score from required arg
        ratio, with a small bonus for providing useful optional args.

        For tools without required args (e.g., search_recipes): scores
        based on whether useful optional args are provided, creating
        variance between completions that include different arg sets.

        Returns:
            Float in [0.0, 1.0]
        """
        tool_call = self._extract_tool_call(completion)
        if tool_call is None:
            return 0.0

        tool_name = tool_call.get("name", "")
        args = tool_call.get("arguments", {})

        if tool_name not in AVAILABLE_TOOLS:
            return 0.0

        tool_def = AVAILABLE_TOOLS[tool_name]
        required = tool_def["required_args"]
        optional = tool_def["optional_args"]

        if required:
            # Required args are primary signal
            required_ratio = sum(1 for a in required if a in args) / len(required)
            # Small bonus for useful optional args
            optional_bonus = 0.0
            if optional and required_ratio > 0.5:
                used_optional = sum(1 for a in optional if a in args)
                optional_bonus = min(used_optional / len(optional), 1.0) * 0.15
            return min(required_ratio * 0.85 + optional_bonus, 1.0)

        # No required args
        if not optional:
            return 1.0  # Tool takes no args (e.g., get_daily_weather)

        # Score based on useful optional args provided
        used = sum(1 for a in optional if a in args)
        if used == 0:
            return 0.4  # Called tool but with no args at all

        # Continuous score based on optional arg coverage
        ratio = used / len(optional)
        return 0.4 + ratio * 0.6  # Range: 0.4 - 1.0

    def reward_query_expansion(
        self,
        completion: str,
        context: str,
        expected_keywords: list[str] | None = None,
    ) -> float:
        """Score search query quality with keyword coverage.

        Uses expected_query_keywords from prompts for objective,
        per-prompt scoring that creates high variance between completions.
        This is the primary differentiator for search-related GRPO groups.

        Scoring breakdown:
          - 0.0:  No query provided
          - 0.2:  Base for having a non-empty query
          - +0.0-0.45: Keyword coverage (fraction of expected keywords found)
          - +0.0-0.15: Query length/specificity bonus
          - +0.1: OR expansion bonus
          - +0.1: Specificity keyword bonus

        Returns:
            Float in [0.0, 1.0]
        """
        tool_call = self._extract_tool_call(completion)
        if tool_call is None or tool_call.get("name") != "search_recipes":
            return 0.5  # N/A — not a search task

        query = tool_call.get("arguments", {}).get("query", "")
        if not query:
            return 0.0

        score = 0.2  # Base: has a query

        # Keyword coverage — the primary differentiation signal
        if expected_keywords:
            query_lower = query.lower()
            matched = sum(1 for kw in expected_keywords if kw.lower() in query_lower)
            keyword_ratio = matched / len(expected_keywords)
            score += keyword_ratio * 0.45  # Up to +0.45

        # Query length/specificity bonus (continuous)
        word_count = len(query.split())
        if word_count >= 2:
            score += min((word_count - 1) / 8, 0.15)  # Up to +0.15

        # OR expansion
        if " OR " in query or "|" in query:
            score += 0.1

        # Specificity keywords
        specificity = [
            "recipe",
            "recipes",
            "method",
            "technique",
            "ideas",
            "ways",
            "how to",
            "dishes",
        ]
        if any(kw in query.lower() for kw in specificity):
            score += 0.1

        return min(score, 1.0)

    def reward_no_tool(self, completion: str, expected_tool: str | None) -> float:
        """Score correct non-tool-call behavior with response quality.

        When expected_tool is None, the model should NOT produce a tool call.
        Uses response length as a continuous quality proxy to differentiate
        completions within a GRPO group.

        Returns:
            Float in [0.0, 1.0]
        """
        if expected_tool is not None:
            return 0.5  # N/A — not a no-tool scenario

        tool_call = self._extract_tool_call(completion)
        if tool_call is not None:
            return 0.0  # Incorrectly called a tool

        # Correct: no tool call. Score response substance for differentiation.
        text = completion.strip()
        length = len(text)
        if length == 0:
            return 0.3  # Empty response
        elif length < 20:
            return 0.4 + (length / 20) * 0.2  # 0.4-0.6
        elif length <= 300:
            return 0.7 + min(length / 300, 1.0) * 0.3  # 0.7-1.0
        else:
            # Diminishing returns for very long responses
            return max(0.7, 1.0 - (length - 300) / 2000)

    def compute_total_reward(
        self,
        completion: str,
        prompt: str,
        expected_tool: str | None = None,
        expected_query_keywords: list[str] | None = None,
    ) -> float:
        """Compute weighted total reward with keyword-aware scoring.

        For prompts where no tool is expected (expected_tool=None),
        uses the no-tool reward which varies by response quality.

        For tool prompts, combines four reward dimensions with
        configurable weights.  The query expansion dimension uses
        expected_query_keywords for per-prompt, objective scoring
        that creates high variance across completions.
        """
        if expected_tool is None:
            no_tool_score = self.reward_no_tool(completion, expected_tool)
            if no_tool_score > 0:
                return no_tool_score  # Varies by response quality (0.3-1.0)
            # Incorrectly called a tool — small credit for well-formed JSON
            json_score = self.reward_json_validity(completion)
            return json_score * 0.15

        # Tool expected — score all dimensions
        rewards = {
            "json": self.reward_json_validity(completion) * self.json_weight,
            "tool": self.reward_tool_name(completion, expected_tool) * self.tool_weight,
            "args": self.reward_argument_completeness(completion) * self.args_weight,
            "query": self.reward_query_expansion(
                completion, prompt, expected_keywords=expected_query_keywords
            )
            * self.query_weight,
        }

        total_weight = (
            self.json_weight + self.tool_weight + self.args_weight + self.query_weight
        )
        return sum(rewards.values()) / total_weight
