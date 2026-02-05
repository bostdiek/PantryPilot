"""Generate training conversations by calling the real PantryPilot backend.

This script authenticates as each synthetic user persona and sends queries
from the query templates to the chat streaming endpoint. The conversations
are automatically captured by the backend's training data capture system.

Execution Modes:
    Concurrent (default): All personas run in parallel
        - Estimated time: 20-25 minutes for 1,000 samples
        - Limited by longest persona (family_fiona: 200 samples × 6s)
        - Recommended for local execution on developer machine

    Sequential: Personas run one after another
        - Estimated time: 2-2.5 hours for 1,000 samples
        - More predictable resource usage
        - Use for constrained environments

Rate Limits:
    - Redis rate limiter: 10 requests per 60 seconds per user
    - Weather API: No hard limit, 20-minute cache per location
    - Brave Search: ~500/day free tier (plenty for 200 calls)
    - Bottleneck: Redis rate limiter (~6 seconds per conversation)

Usage (local):
    PYTHONPATH=./src uv run python -m training.generate_conversations

Usage (AML notebook):
    %pip install httpx python-dotenv
    # Set API_BASE_URL to your deployed backend
    # Set DATABASE_URL if seeding is needed

Environment Variables:
    API_BASE_URL: Backend URL (default: http://localhost:8000)
    DATABASE_URL: Cloud database URL (optional, for seeding)
    SEED_BEFORE_GENERATE: Set to "true" to seed personas before generating
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from training.personas import PERSONAS, SAMPLE_TARGETS
from training.query_templates import (
    format_query,
    get_conversation_scenarios,
    get_persona_queries,
)
from training.seed_database import SYNTHETIC_PASSWORD


# Retry configuration
MAX_RETRIES = 5
BASE_RETRY_DELAY = 2.0  # seconds
MAX_RETRY_DELAY = 60.0  # seconds

# Request delay configuration (seconds between requests)
# Default to 7s to safely stay under 10 req/60s rate limit (6s theoretical minimum)
DEFAULT_REQUEST_DELAY = float(os.getenv("REQUEST_DELAY_SECONDS", "7.0"))
DEFAULT_MULTI_TURN_DELAY = float(os.getenv("MULTI_TURN_DELAY_SECONDS", "8.0"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _calculate_retry_delay(attempt: int) -> float:
    """Calculate exponential backoff delay for retry attempts.

    Args:
        attempt: Current retry attempt (0-indexed)

    Returns:
        Delay in seconds with jitter
    """
    delay = min(BASE_RETRY_DELAY * (2**attempt), MAX_RETRY_DELAY)
    # Add jitter to avoid thundering herd
    jitter = random.uniform(0, delay * 0.1)
    return delay + jitter


def _load_env_files() -> None:
    """Load environment files."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    for fname in (".env", ".env.dev"):
        for p in Path(__file__).resolve().parents:
            candidate = p / fname
            if candidate.exists():
                load_dotenv(dotenv_path=candidate, override=False)
                return


@dataclass
class ConversationResult:
    """Result of a single conversation."""

    persona: str
    conversation_id: str
    query: str
    response_text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class FailedConversation:
    """Record of a failed conversation for retry."""

    persona: str
    query: str
    conversation_id: str | None = None
    error: str = ""
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class GenerationStats:
    """Statistics for the generation run."""

    total_conversations: int = 0
    successful_conversations: int = 0
    failed_conversations: int = 0
    total_tool_calls: int = 0
    total_duration_seconds: float = 0.0
    conversations_per_persona: dict[str, int] = field(default_factory=dict)
    failures: list[FailedConversation] = field(default_factory=list)
    failures: list[FailedConversation] = field(default_factory=list)


class ConversationGenerator:
    """Generates training conversations by calling the PantryPilot backend."""

    def __init__(
        self,
        api_base_url: str = "http://localhost:8000",
        timeout: float = 120.0,
        request_delay: float = DEFAULT_REQUEST_DELAY,
        multi_turn_delay: float = DEFAULT_MULTI_TURN_DELAY,
    ):
        """Initialize the generator.

        Args:
            api_base_url: Base URL of the PantryPilot backend
            timeout: Request timeout in seconds
            request_delay: Delay between single-turn requests (seconds)
            multi_turn_delay: Delay between multi-turn conversation turns (seconds)
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout = timeout
        self.request_delay = request_delay
        self.multi_turn_delay = multi_turn_delay
        self.tokens: dict[str, str] = {}  # persona -> access_token
        self.stats = GenerationStats()

        logger.info(
            "Initialized with request_delay=%.1fs, multi_turn_delay=%.1fs",
            request_delay,
            multi_turn_delay,
        )

    async def login(self, client: httpx.AsyncClient, persona_name: str) -> str | None:
        """Login as a synthetic user and get access token.

        Args:
            client: HTTP client
            persona_name: Name of the persona

        Returns:
            Access token or None if login failed
        """
        persona = PERSONAS[persona_name]
        username = persona["user_id"]  # e.g., "synthetic-veggie-val"

        try:
            response = await client.post(
                f"{self.api_base_url}/api/v1/auth/login",
                data={
                    "username": username,
                    "password": SYNTHETIC_PASSWORD,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 200:
                token_data = response.json()
                token = token_data["access_token"]
                self.tokens[persona_name] = token
                logger.info("Logged in as %s", username)
                return token
            else:
                logger.error(
                    "Login failed for %s: %s - %s",
                    username,
                    response.status_code,
                    response.text,
                )
                return None

        except Exception as e:
            logger.exception("Login error for %s: %s", username, e)
            return None

    async def send_chat_message_with_retry(
        self,
        client: httpx.AsyncClient,
        persona_name: str,
        message: str,
        conversation_id: str | None = None,
    ) -> ConversationResult:
        """Send a chat message with retry logic for rate limiting.

        Args:
            client: HTTP client
            persona_name: Name of the persona
            message: User message to send
            conversation_id: Optional conversation ID (creates new if None)

        Returns:
            ConversationResult with response data
        """
        for attempt in range(MAX_RETRIES):
            result = await self.send_chat_message(
                client, persona_name, message, conversation_id
            )

            # Check if we got a 429 error
            if result.error and "429" in result.error:
                if attempt < MAX_RETRIES - 1:
                    delay = _calculate_retry_delay(attempt)
                    logger.warning(
                        "Rate limited (429), retry %d/%d after %.1fs",
                        attempt + 1,
                        MAX_RETRIES,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(
                        "Rate limited after %d retries, giving up",
                        MAX_RETRIES,
                    )

            return result

        # Shouldn't reach here, but return last result
        return result

    async def send_chat_message(  # noqa: C901
        self,
        client: httpx.AsyncClient,
        persona_name: str,
        message: str,
        conversation_id: str | None = None,
    ) -> ConversationResult:
        """Send a chat message and collect the streaming response.

        Args:
            client: HTTP client
            persona_name: Name of the persona
            message: User message to send
            conversation_id: Optional conversation ID (creates new if None)

        Returns:
            ConversationResult with response data
        """
        token = self.tokens.get(persona_name)
        if not token:
            return ConversationResult(
                persona=persona_name,
                conversation_id="",
                query=message,
                response_text="",
                error="Not authenticated",
            )

        conv_id = conversation_id or str(uuid4())
        start_time = time.time()

        try:
            # Send streaming request
            async with client.stream(
                "POST",
                f"{self.api_base_url}/api/v1/chat/conversations/{conv_id}/messages/stream",
                json={"content": message},
                headers={"Authorization": f"Bearer {token}"},
                timeout=self.timeout,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    return ConversationResult(
                        persona=persona_name,
                        conversation_id=conv_id,
                        query=message,
                        response_text="",
                        error=f"HTTP {response.status_code}: {error_text.decode()}",
                        duration_seconds=time.time() - start_time,
                    )

                # Collect streaming response
                response_text = ""
                tool_calls: list[dict[str, Any]] = []

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    try:
                        event_data = json.loads(line[6:])
                        event_type = event_data.get("event")

                        if event_type == "message.delta":
                            delta = event_data.get("data", {}).get("delta", "")
                            response_text += delta

                        elif event_type == "tool.started":
                            tool_calls.append(
                                {
                                    "name": event_data.get("data", {}).get("name"),
                                    "status": "started",
                                }
                            )

                        elif event_type == "tool.result":
                            # Update last tool call with result
                            if tool_calls:
                                tool_calls[-1]["status"] = "completed"

                        elif event_type == "error":
                            return ConversationResult(
                                persona=persona_name,
                                conversation_id=conv_id,
                                query=message,
                                response_text=response_text,
                                tool_calls=tool_calls,
                                error=event_data.get("data", {}).get("message"),
                                duration_seconds=time.time() - start_time,
                            )

                    except json.JSONDecodeError:
                        continue

                return ConversationResult(
                    persona=persona_name,
                    conversation_id=conv_id,
                    query=message,
                    response_text=response_text,
                    tool_calls=tool_calls,
                    duration_seconds=time.time() - start_time,
                )

        except Exception as e:
            return ConversationResult(
                persona=persona_name,
                conversation_id=conv_id,
                query=message,
                response_text="",
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

    async def generate_single_turn_conversations(
        self,
        client: httpx.AsyncClient,
        persona_name: str,
        num_queries: int = 10,
    ) -> list[ConversationResult]:
        """Generate single-turn conversations for a persona.

        Args:
            client: HTTP client
            persona_name: Name of the persona
            num_queries: Number of queries to send

        Returns:
            List of conversation results
        """
        results: list[ConversationResult] = []

        # Get queries for this persona
        queries = get_persona_queries(persona_name)
        persona = PERSONAS[persona_name]

        # Randomly sample queries if we have more than needed
        if len(queries) > num_queries:
            selected_queries = random.sample(queries, num_queries)
        else:
            # Repeat queries if needed
            selected_queries = queries * (num_queries // len(queries) + 1)
            selected_queries = selected_queries[:num_queries]

        for i, query_template in enumerate(selected_queries):
            # Format query with persona context
            query = format_query(query_template, persona)

            logger.info(
                "[%s] Query %d/%d: %s",
                persona_name,
                i + 1,
                num_queries,
                query[:80] + "..." if len(query) > 80 else query,
            )

            result = await self.send_chat_message_with_retry(
                client, persona_name, query
            )
            results.append(result)

            # Update stats
            self.stats.total_conversations += 1
            if result.error:
                self.stats.failed_conversations += 1
                self.stats.failures.append(
                    FailedConversation(
                        persona=persona_name,
                        query=query,
                        conversation_id=result.conversation_id,
                        error=result.error,
                    )
                )
                logger.warning("Failed: %s", result.error)
            else:
                self.stats.successful_conversations += 1
                self.stats.total_tool_calls += len(result.tool_calls)
                logger.info(
                    "Success: %d chars, %d tool calls, %.1fs",
                    len(result.response_text),
                    len(result.tool_calls),
                    result.duration_seconds,
                )

            # Delay between requests to respect rate limits
            if i < num_queries - 1:  # Don't delay after last request
                await asyncio.sleep(self.request_delay)

        return results

    async def generate_multi_turn_conversations(
        self,
        client: httpx.AsyncClient,
        persona_name: str,
        num_conversations: int = 3,
    ) -> list[list[ConversationResult]]:
        """Generate multi-turn conversations for a persona.

        Args:
            client: HTTP client
            persona_name: Name of the persona
            num_conversations: Number of multi-turn conversations

        Returns:
            List of conversation lists (each is a multi-turn conversation)
        """
        results: list[list[ConversationResult]] = []

        # Get conversation scenarios for this persona
        scenarios = get_conversation_scenarios(persona_name)
        persona = PERSONAS[persona_name]

        if not scenarios:
            logger.warning("No conversation scenarios for %s", persona_name)
            return results

        # Select scenarios
        selected = random.sample(
            scenarios,
            min(num_conversations, len(scenarios)),
        )

        for i, scenario in enumerate(selected):
            conversation_id = str(uuid4())
            conversation_results: list[ConversationResult] = []

            logger.info(
                "[%s] Multi-turn conversation %d/%d: %d turns",
                persona_name,
                i + 1,
                len(selected),
                len(scenario),
            )

            for turn_idx, turn in enumerate(scenario):
                query = format_query(turn, persona)

                result = await self.send_chat_message_with_retry(
                    client,
                    persona_name,
                    query,
                    conversation_id=conversation_id,
                )
                conversation_results.append(result)

                # Update stats
                self.stats.total_conversations += 1
                if result.error:
                    self.stats.failed_conversations += 1
                    self.stats.failures.append(
                        FailedConversation(
                            persona=persona_name,
                            query=query,
                            conversation_id=conversation_id,
                            error=result.error,
                        )
                    )
                    logger.warning("Turn failed: %s", result.error)
                    break  # Stop this conversation on error
                else:
                    self.stats.successful_conversations += 1
                    self.stats.total_tool_calls += len(result.tool_calls)

                # Delay between turns to respect rate limits
                if turn_idx < len(scenario) - 1:  # Don't delay after last turn
                    await asyncio.sleep(self.multi_turn_delay)

            results.append(conversation_results)

        return results

    async def generate_for_persona(
        self,
        client: httpx.AsyncClient,
        persona_name: str,
        target_samples: int | None = None,
    ) -> dict[str, Any]:
        """Generate all training data for a single persona.

        Args:
            client: HTTP client
            persona_name: Name of the persona
            target_samples: Target number of samples (uses SAMPLE_TARGETS if None)

        Returns:
            Summary of generated data
        """
        target = target_samples or SAMPLE_TARGETS.get(persona_name, 100)

        # Login first
        token = await self.login(client, persona_name)
        if not token:
            return {
                "persona": persona_name,
                "error": "Login failed",
                "single_turn": [],
                "multi_turn": [],
            }

        # Allocate between single-turn and multi-turn
        single_turn_count = int(target * 0.7)  # 70% single-turn
        multi_turn_count = max(2, int(target * 0.3 / 4))  # 30% multi-turn (avg 4 turns)

        logger.info(
            "Generating for %s: %d single-turn, %d multi-turn conversations",
            persona_name,
            single_turn_count,
            multi_turn_count,
        )

        # Generate conversations
        single_results = await self.generate_single_turn_conversations(
            client,
            persona_name,
            single_turn_count,
        )

        multi_results = await self.generate_multi_turn_conversations(
            client,
            persona_name,
            multi_turn_count,
        )

        # Track per-persona counts
        persona_total = len(single_results) + sum(len(c) for c in multi_results)
        self.stats.conversations_per_persona[persona_name] = persona_total

        return {
            "persona": persona_name,
            "single_turn_count": len(single_results),
            "multi_turn_conversations": len(multi_results),
            "multi_turn_total_messages": sum(len(c) for c in multi_results),
            "single_turn": single_results,
            "multi_turn": multi_results,
        }

    async def generate_all(
        self,
        personas: list[str] | None = None,
        target_per_persona: int | None = None,
        concurrent: bool = True,
    ) -> dict[str, Any]:
        """Generate training data for all personas.

        Args:
            personas: List of persona names (all if None)
            target_per_persona: Override target samples per persona
            concurrent: Run personas concurrently (default: True)

        Returns:
            Summary of all generated data
        """
        selected_personas = personas or list(PERSONAS.keys())

        logger.info(
            "Starting %s generation for %d personas",
            "concurrent" if concurrent else "sequential",
            len(selected_personas),
        )
        start_time = time.time()

        results: dict[str, Any] = {}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if concurrent:
                # Run all personas concurrently
                tasks = [
                    self._generate_persona_task(
                        client, persona_name, target_per_persona
                    )
                    for persona_name in selected_personas
                ]
                persona_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for persona_name, result in zip(
                    selected_personas, persona_results, strict=True
                ):
                    if isinstance(result, Exception):
                        logger.error("Persona %s failed: %s", persona_name, result)
                        results[persona_name] = {
                            "persona": persona_name,
                            "error": str(result),
                            "single_turn": [],
                            "multi_turn": [],
                        }
                    else:
                        results[persona_name] = result
            else:
                # Sequential execution (original behavior)
                for persona_name in selected_personas:
                    logger.info("\n=== Processing persona: %s ===", persona_name)
                    results[persona_name] = await self.generate_for_persona(
                        client,
                        persona_name,
                        target_per_persona,
                    )

                    # Delay between personas
                    await asyncio.sleep(2.0)

        self.stats.total_duration_seconds = time.time() - start_time

        # Print summary
        self._print_summary()

        return results

    async def _generate_persona_task(
        self,
        client: httpx.AsyncClient,
        persona_name: str,
        target_samples: int | None,
    ) -> dict[str, Any]:
        """Wrapper for concurrent persona generation with logging.

        Args:
            client: HTTP client
            persona_name: Name of the persona
            target_samples: Target number of samples

        Returns:
            Generation results for the persona
        """
        logger.info("Starting persona: %s", persona_name)
        try:
            result = await self.generate_for_persona(
                client,
                persona_name,
                target_samples,
            )
            logger.info("Completed persona: %s", persona_name)
            return result
        except Exception as e:
            logger.error("Failed persona %s: %s", persona_name, e)
            raise

    def _print_summary(self) -> None:
        """Print generation summary."""
        logger.info("\n" + "=" * 60)
        logger.info("GENERATION SUMMARY")
        logger.info("=" * 60)
        logger.info("Total conversations: %d", self.stats.total_conversations)
        logger.info("Successful: %d", self.stats.successful_conversations)
        logger.info("Failed: %d", self.stats.failed_conversations)
        logger.info("Total tool calls: %d", self.stats.total_tool_calls)
        logger.info("Total duration: %.1f seconds", self.stats.total_duration_seconds)
        logger.info("")
        logger.info("Per-persona breakdown:")
        for persona, count in self.stats.conversations_per_persona.items():
            logger.info("  %s: %d conversations", persona, count)

        if self.stats.failures:
            logger.warning("")
            logger.warning("Failed conversations: %d", len(self.stats.failures))
            self._save_failures()

        logger.info("=" * 60)

    def _save_failures(self) -> None:
        """Save failed conversations to JSON file for retry."""
        failures_file = Path("failed_conversations.json")

        # Load existing failures if file exists
        existing_failures: list[dict[str, Any]] = []
        if failures_file.exists():
            try:
                with failures_file.open() as f:
                    existing_failures = json.load(f)
            except Exception as e:
                logger.warning("Could not load existing failures: %s", e)

        # Convert new failures to dicts
        new_failures = [
            {
                "persona": f.persona,
                "query": f.query,
                "conversation_id": f.conversation_id,
                "error": f.error,
                "timestamp": f.timestamp,
            }
            for f in self.stats.failures
        ]

        # Merge with existing
        all_failures = existing_failures + new_failures

        # Save to file
        with failures_file.open("w") as f:
            json.dump(all_failures, f, indent=2)

        logger.warning("Saved %d failures to %s", len(all_failures), failures_file)
        logger.warning("To retry: Load file and re-run failed queries manually")
        if self.stats.failures:
            logger.warning("")
            logger.warning("Failed conversations: %d", len(self.stats.failures))
            logger.warning("Saving failures to failed_conversations.json for retry...")
            self._save_failures()

        logger.info("=" * 60)

    def _save_failures(self) -> None:
        """Save failed conversations to JSON file for retry."""
        failures_file = Path("failed_conversations.json")

        # Load existing failures if file exists
        existing_failures = []
        if failures_file.exists():
            try:
                with failures_file.open() as f:
                    existing_data = json.load(f)
                    existing_failures = [
                        FailedConversation(**item) for item in existing_data
                    ]
            except Exception as e:
                logger.warning("Could not load existing failures: %s", e)

        # Merge with new failures
        all_failures = existing_failures + self.stats.failures

        # Save to file
        with failures_file.open("w") as f:
            json.dump(
                [vars(failure) for failure in all_failures],
                f,
                indent=2,
            )

        logger.info("Saved %d failures to %s", len(all_failures), failures_file)


async def run_generation(
    api_base_url: str | None = None,
    personas: list[str] | None = None,
    target_per_persona: int | None = None,
    seed_first: bool = False,
    concurrent: bool = True,
    request_delay: float | None = None,
    multi_turn_delay: float | None = None,
) -> dict[str, Any]:
    """Main entry point for generation.

    Args:
        api_base_url: Backend URL (uses API_BASE_URL env var if None)
        personas: Specific personas to generate (all if None)
        target_per_persona: Override target samples
        seed_first: Whether to seed database before generating
        concurrent: Run personas concurrently (default: True)
        request_delay: Delay between single-turn requests (env var if None)
        multi_turn_delay: Delay between multi-turn turns (env var if None)

    Returns:
        Generation results
    """
    _load_env_files()

    # Get API URL
    url = api_base_url or os.getenv("API_BASE_URL", "http://localhost:8000")

    # Optionally seed first
    if seed_first or os.getenv("SEED_BEFORE_GENERATE", "").lower() == "true":
        logger.info("Seeding database with personas...")
        from training.seed_database import run_seeding

        await run_seeding()
        logger.info("Seeding complete")

    # Generate conversations
    generator = ConversationGenerator(
        api_base_url=url,
        request_delay=request_delay or DEFAULT_REQUEST_DELAY,
        multi_turn_delay=multi_turn_delay or DEFAULT_MULTI_TURN_DELAY,
    )
    return await generator.generate_all(
        personas=personas,
        target_per_persona=target_per_persona,
        concurrent=concurrent,
    )


if __name__ == "__main__":
    # Default: Concurrent execution for all personas (~20-25 minutes)
    asyncio.run(run_generation())

    # Examples:
    # Sequential execution (slower but more predictable)
    # asyncio.run(run_generation(concurrent=False))

    # Seed database first, then generate
    # asyncio.run(run_generation(seed_first=True))

    # Test with specific personas
    # asyncio.run(run_generation(personas=["veggie_val", "solo_sam"]))

    # Override target samples (useful for testing)
    # asyncio.run(run_generation(target_per_persona=10))
