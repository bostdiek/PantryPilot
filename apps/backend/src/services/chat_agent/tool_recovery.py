"""Bounded infrastructure recovery for explicitly registered read-only tools."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Concatenate, TypeGuard

from pydantic_ai import RunContext

from core.observability import ProductTelemetryEventName, get_current_span
from core.transient_errors import classify_tool_error
from services.chat_agent.deps import ChatAgentDeps


MAX_ATTEMPTS = 3
ATTEMPT_TIMEOUT_SECONDS = 10.0
# Weather can make three sequential 10s requests; URL fetches and embeddings allow 30s.
EXTENDED_ATTEMPT_TIMEOUT_SECONDS = 33.0
MAX_ELAPSED_SECONDS = 35.0
MAX_TOTAL_BACKOFF_SECONDS = 2.0
MAX_BACKOFF_SECONDS = 0.8
MAX_MODEL_CALLS_AFTER_FAILURE = 2
EXTENDED_TIMEOUT_TOOLS = frozenset(
    {"search_recipes", "get_daily_weather", "fetch_url_as_markdown"}
)

type FailureResult = dict[str, str | bool]
FAILURE_CODES = {
    "transient_database_error",
    "transient_network_error",
    "transient_service_error",
    "tool_unavailable",
}
TOOL_LABELS = {
    "get_meal_plan_history": "Meal plan history",
    "search_recipes": "Recipe search",
    "get_recipe_details": "Recipe details",
    "get_daily_weather": "Weather lookup",
    "web_search": "Web search",
    "fetch_url_as_markdown": "Web page lookup",
}


def is_failure_result(value: object) -> TypeGuard[FailureResult]:
    """Recognize only the internal, sanitized recovery contract."""
    if not isinstance(value, dict):
        return False
    code = value.get("error_code")
    retryable = value.get("retryable")
    return (
        isinstance(code, str)
        and code in FAILURE_CODES
        and isinstance(retryable, bool)
        and any(
            value == failure_result(code, retryable=retryable, tool_name=tool_name)
            for tool_name in (None, *TOOL_LABELS)
        )
    )


def failure_result(
    code: str, *, retryable: bool = True, tool_name: str | None = None
) -> FailureResult:
    """Expose only a stable code and actionable, sanitized guidance."""
    label = TOOL_LABELS.get(tool_name, "This lookup") if tool_name else "This lookup"
    message = (
        f"{label} temporarily failed. Use available results or ask the user to retry."
        if retryable
        else f"{label} is unavailable for this turn. Do not call it again."
    )
    return {
        "status": "error",
        "error_code": code,
        "retryable": retryable,
        "message": message,
    }


def _record_attempt(
    *,
    tool_name: str,
    attempt: int,
    classification: str,
    backoff_seconds: float,
    latency_ms: int,
    outcome: str,
) -> None:
    get_current_span().add_event(
        ProductTelemetryEventName.ASSISTANT_TOOL_RETRY.value,
        attributes={
            "tool.name": tool_name,
            "tool.attempt": attempt,
            "tool.classification": classification,
            "tool.backoff_ms": int(backoff_seconds * 1000),
            "tool.latency_ms": latency_ms,
            "tool.outcome": outcome,
        },
    )


async def _allow_model_call(name: str, deps: ChatAgentDeps) -> bool:
    async with deps.retry_budget_lock:
        if name not in deps.failed_tools:
            return True
        calls = deps.model_calls_after_failure.get(name, 0)
        if calls >= MAX_MODEL_CALLS_AFTER_FAILURE:
            return False
        deps.model_calls_after_failure[name] = calls + 1
        return True


def resilient_read_tool[**P, T](
    name: str,
    function: Callable[Concatenate[RunContext[ChatAgentDeps], P], Awaitable[T]],
) -> Callable[Concatenate[RunContext[ChatAgentDeps], P], Awaitable[T | FailureResult]]:
    """Apply bounded retries only where registration proves read-only."""

    @wraps(function)
    async def wrapped(
        ctx: RunContext[ChatAgentDeps], *args: P.args, **kwargs: P.kwargs
    ) -> T | FailureResult:
        if not await _allow_model_call(name, ctx.deps):
            _record_attempt(
                tool_name=name,
                attempt=0,
                classification="model_budget_exhausted",
                backoff_seconds=0,
                latency_ms=0,
                outcome="terminal",
            )
            return failure_result("tool_unavailable", retryable=False, tool_name=name)

        deadline = time.monotonic() + MAX_ELAPSED_SECONDS
        attempt_timeout = (
            EXTENDED_ATTEMPT_TIMEOUT_SECONDS
            if name in EXTENDED_TIMEOUT_TOOLS
            else ATTEMPT_TIMEOUT_SECONDS
        )
        total_backoff = 0.0
        for attempt in range(1, MAX_ATTEMPTS + 1):
            started = time.monotonic()
            try:
                remaining = deadline - started
                if remaining <= 0:
                    raise TimeoutError
                async with asyncio.timeout(min(attempt_timeout, remaining)):
                    result = await function(ctx, *args, **kwargs)
            except Exception as exc:
                classification = classify_tool_error(exc)
                latency_ms = int((time.monotonic() - started) * 1000)
                if classification is None:
                    _record_attempt(
                        tool_name=name,
                        attempt=attempt,
                        classification="terminal",
                        backoff_seconds=0,
                        latency_ms=latency_ms,
                        outcome="terminal",
                    )
                    raise

                remaining = deadline - time.monotonic()
                if attempt == MAX_ATTEMPTS or remaining <= 0:
                    _record_attempt(
                        tool_name=name,
                        attempt=attempt,
                        classification=classification,
                        backoff_seconds=0,
                        latency_ms=latency_ms,
                        outcome="exhausted",
                    )
                    ctx.deps.failed_tools.add(name)
                    return failure_result(classification, tool_name=name)

                maximum = min(
                    MAX_BACKOFF_SECONDS,
                    0.1 * 2 ** (attempt - 1),
                    MAX_TOTAL_BACKOFF_SECONDS - total_backoff,
                    remaining,
                )
                backoff = random.uniform(0, maximum)
                _record_attempt(
                    tool_name=name,
                    attempt=attempt,
                    classification=classification,
                    backoff_seconds=backoff,
                    latency_ms=latency_ms,
                    outcome="retrying",
                )
                total_backoff += backoff
                await asyncio.sleep(backoff)
            else:
                if attempt > 1:
                    ctx.deps.recovered_tools.add(name)
                _record_attempt(
                    tool_name=name,
                    attempt=attempt,
                    classification="none",
                    backoff_seconds=0,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    outcome="recovered" if attempt > 1 else "success",
                )
                return result

        raise AssertionError("Retry loop must return or raise")

    return wrapped
