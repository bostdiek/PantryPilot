"""Tests for the assistant's read-only infrastructure recovery boundary."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from google.genai import errors as genai_errors
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from core.transient_errors import classify_tool_error
from models.users import User
from services.ai.html_extractor import HTMLExtractionService
from services.chat_agent.agent import get_chat_agent
from services.chat_agent.deps import ChatAgentDeps
from services.chat_agent.tool_recovery import (
    EXTENDED_ATTEMPT_TIMEOUT_SECONDS,
    EXTENDED_TIMEOUT_TOOLS,
    MAX_ATTEMPTS,
    MAX_ELAPSED_SECONDS,
    failure_result,
    is_failure_result,
    resilient_read_tool,
)
from services.chat_agent.tools.weather import tool_get_daily_weather
from services.chat_agent.tools.web import (
    tool_fetch_url_as_markdown,
    tool_web_search,
)
from services.web_search import search_web


def _deps(db: object) -> ChatAgentDeps:
    return ChatAgentDeps(
        db=cast(AsyncSession, db),
        user=cast(User, object()),
        current_datetime=datetime.now(UTC),
        user_timezone="UTC",
    )


def _ctx(deps: ChatAgentDeps) -> RunContext[ChatAgentDeps]:
    return cast(RunContext[ChatAgentDeps], type("ToolContext", (), {"deps": deps})())


class _Db:
    def __init__(self) -> None:
        self.rollback_started = asyncio.Event()
        self.allow_rollback = asyncio.Event()
        self.operations: list[str] = []

    async def rollback(self) -> None:
        self.operations.append("rollback")
        self.rollback_started.set()
        await self.allow_rollback.wait()


@pytest.mark.asyncio
async def test_given_db_failure_when_sibling_waits_then_rolls_back_first() -> None:
    # Arrange
    db = _Db()
    deps = _deps(db)
    failure = OperationalError(
        "select 1", {}, Exception("sensitive"), connection_invalidated=True
    )

    async def failing() -> None:
        async with deps.use_db():
            db.operations.append("failed-query")
            raise failure

    async def sibling() -> None:
        async with deps.use_db():
            db.operations.append("sibling-query")

    # Act
    first = asyncio.create_task(failing())
    await db.rollback_started.wait()
    second = asyncio.create_task(sibling())
    await asyncio.sleep(0)
    assert db.operations == ["failed-query", "rollback"]
    db.allow_rollback.set()
    with pytest.raises(OperationalError):
        await first
    await second

    # Assert
    assert db.operations == ["failed-query", "rollback", "sibling-query"]


@pytest.mark.asyncio
async def test_given_transient_db_failure_when_retried_then_rollback_precedes_repeat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = _Db()
    db.allow_rollback.set()
    deps = _deps(db)
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.random.uniform", lambda _low, _high: 0
    )
    failure = OperationalError(
        "select 1", {}, Exception("private SQL"), connection_invalidated=True
    )

    async def lookup(ctx: RunContext[ChatAgentDeps]) -> dict[str, bool]:
        async with ctx.deps.use_db():
            db.operations.append("query")
            if db.operations.count("query") == 1:
                raise failure
            return {"ready": True}

    result = await resilient_read_tool("search_recipes", lookup)(_ctx(deps))

    assert result == {"ready": True}
    assert db.operations == ["query", "rollback", "query"]
    assert "search_recipes" in deps.recovered_tools


@pytest.mark.asyncio
async def test_given_transient_error_when_retry_succeeds_then_returns_original_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    attempts = 0
    records: list[dict[str, object]] = []
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery._record_attempt",
        lambda **kwargs: records.append(kwargs),
    )
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.random.uniform", lambda _low, high: high
    )

    async def lookup(_ctx: RunContext[ChatAgentDeps]) -> dict[str, int]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("sensitive connection detail")
        return {"count": 3}

    # Act
    result = await resilient_read_tool("lookup", lookup)(_ctx(_deps(object())))

    # Assert
    assert result == {"count": 3}
    assert attempts == 2
    assert [record["outcome"] for record in records] == ["retrying", "recovered"]
    assert records[0]["backoff_seconds"] == 0.1
    assert "sensitive" not in str(records)


@pytest.mark.asyncio
async def test_given_repeated_transient_error_when_exhausted_then_bounded_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    attempts = 0
    waits: list[float] = []

    async def fake_sleep(delay: float) -> None:
        waits.append(delay)

    monkeypatch.setattr("services.chat_agent.tool_recovery.asyncio.sleep", fake_sleep)
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.random.uniform", lambda _low, high: high
    )

    async def lookup(_ctx: RunContext[ChatAgentDeps]) -> None:
        nonlocal attempts
        attempts += 1
        raise httpx.TimeoutException("private hostname")

    # Act
    result = await resilient_read_tool("lookup", lookup)(_ctx(_deps(object())))

    # Assert
    assert attempts == MAX_ATTEMPTS == 3
    assert sum(waits) <= 2
    assert result == {
        "status": "error",
        "error_code": "transient_network_error",
        "retryable": True,
        "message": (
            "This lookup temporarily failed. Use available results or ask the user "
            "to retry."
        ),
    }
    assert "private hostname" not in str(result)


@pytest.mark.asyncio
async def test_given_recipe_lookup_failure_when_exhausted_then_uses_contract_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.random.uniform", lambda _low, _high: 0
    )

    async def lookup(_ctx: RunContext[ChatAgentDeps]) -> None:
        raise httpx.ConnectError("secret")

    result = await resilient_read_tool("search_recipes", lookup)(_ctx(_deps(object())))

    assert result == {
        "status": "error",
        "error_code": "transient_network_error",
        "retryable": True,
        "message": (
            "Recipe search temporarily failed. Use available results or ask "
            "the user to retry."
        ),
    }
    assert is_failure_result(result)


@pytest.mark.asyncio
async def test_given_terminal_error_when_tool_runs_then_does_not_retry() -> None:
    # Arrange
    attempts = 0

    async def lookup(_ctx: RunContext[ChatAgentDeps]) -> None:
        nonlocal attempts
        attempts += 1
        raise ValueError("invalid input")

    # Act and assert
    with pytest.raises(ValueError, match="invalid input"):
        await resilient_read_tool("lookup", lookup)(_ctx(_deps(object())))
    assert attempts == 1


@pytest.mark.asyncio
async def test_given_slow_tool_when_deadline_passes_then_returns_bounded_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.ATTEMPT_TIMEOUT_SECONDS", 0.01
    )
    monkeypatch.setattr("services.chat_agent.tool_recovery.MAX_ELAPSED_SECONDS", 0.03)

    async def slow(_ctx: RunContext[ChatAgentDeps]) -> None:
        await asyncio.sleep(1)

    # Act
    result = await asyncio.wait_for(
        resilient_read_tool("slow", slow)(_ctx(_deps(object()))), timeout=0.2
    )

    # Assert
    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert result["error_code"] == "transient_network_error"


def test_given_long_running_read_tools_when_configured_then_budget_covers_fetches() -> (
    None
):
    # Arrange/Act/Assert
    assert {
        "search_recipes",
        "get_daily_weather",
        "fetch_url_as_markdown",
    } <= EXTENDED_TIMEOUT_TOOLS
    assert EXTENDED_ATTEMPT_TIMEOUT_SECONDS > 30.0
    assert MAX_ELAPSED_SECONDS > EXTENDED_ATTEMPT_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_given_slow_fetch_when_within_downstream_timeout_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.ATTEMPT_TIMEOUT_SECONDS", 0.05
    )
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.EXTENDED_ATTEMPT_TIMEOUT_SECONDS", 0.2
    )
    monkeypatch.setattr("services.chat_agent.tool_recovery.MAX_ELAPSED_SECONDS", 0.25)
    attempts = 0

    class SlowExtractor:
        async def fetch_as_markdown(self, _url: str) -> str:
            nonlocal attempts
            attempts += 1
            await asyncio.sleep(0.08)
            return "# Recipe"

    monkeypatch.setattr(
        "services.chat_agent.tools.web._get_markdown_extractor",
        lambda: SlowExtractor(),
    )
    # Act
    result = await resilient_read_tool(
        "fetch_url_as_markdown", tool_fetch_url_as_markdown
    )(_ctx(_deps(object())), "https://example.com/slow")

    # Assert
    assert result["status"] == "ok"
    assert result["content"] == "# Recipe"
    assert attempts == 1


@pytest.mark.asyncio
async def test_given_slow_primary_when_weather_fallback_succeeds_then_returns_forecast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.ATTEMPT_TIMEOUT_SECONDS", 0.05
    )
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.EXTENDED_ATTEMPT_TIMEOUT_SECONDS", 0.2
    )
    monkeypatch.setattr("services.chat_agent.tool_recovery.MAX_ELAPSED_SECONDS", 0.25)
    user = MagicMock()
    user.id = uuid4()
    preferences = MagicMock()
    preferences.latitude = 42.36
    preferences.longitude = -71.06
    preferences.timezone = "America/New_York"
    preferences.units = "imperial"
    preferences.country = "US"
    preferences.city = "Boston"
    preferences.state_or_region = "MA"
    preferences.postal_code = None
    forecast: dict[str, object] = {
        "status": "ok",
        "provider": "weather.gov",
        "days": [],
    }

    async def slow_primary(**_kwargs: object) -> None:
        await asyncio.sleep(0.07)
        raise httpx.ReadTimeout("Open-Meteo timed out")

    async def healthy_fallback(**_kwargs: object) -> dict[str, object]:
        await asyncio.sleep(0.07)
        return forecast

    deps = ChatAgentDeps(
        db=cast(AsyncSession, AsyncMock()),
        user=cast(User, user),
        current_datetime=datetime.now(UTC),
        user_timezone="UTC",
    )
    with (
        patch(
            "services.chat_agent.tools.weather.user_preferences_crud.get_by_user_id",
            new_callable=AsyncMock,
            return_value=preferences,
        ),
        patch(
            "services.weather._fetch_open_meteo",
            new_callable=AsyncMock,
            side_effect=slow_primary,
        ) as open_meteo,
        patch(
            "services.weather._fetch_weather_gov",
            new_callable=AsyncMock,
            side_effect=healthy_fallback,
        ) as weather_gov,
    ):
        # Act
        result = await resilient_read_tool("get_daily_weather", tool_get_daily_weather)(
            _ctx(deps)
        )

    # Assert
    assert result == forecast
    open_meteo.assert_awaited_once()
    weather_gov.assert_awaited_once()


@pytest.mark.asyncio
async def test_given_extended_lookup_stalls_when_budget_expires_then_returns_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.EXTENDED_ATTEMPT_TIMEOUT_SECONDS", 0.1
    )
    monkeypatch.setattr("services.chat_agent.tool_recovery.MAX_ELAPSED_SECONDS", 0.12)
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.random.uniform", lambda _low, _high: 0
    )
    attempts = 0

    async def stalled(_ctx: RunContext[ChatAgentDeps]) -> None:
        nonlocal attempts
        attempts += 1
        await asyncio.sleep(1)

    # Act
    result = await asyncio.wait_for(
        resilient_read_tool("search_recipes", stalled)(_ctx(_deps(object()))),
        timeout=0.3,
    )

    # Assert
    assert result == failure_result(
        "transient_network_error", tool_name="search_recipes"
    )
    assert 1 <= attempts <= MAX_ATTEMPTS


def test_given_agent_registration_when_inspected_then_mutations_are_not_wrapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setattr("services.chat_agent.agent._create_model", TestModel)
    get_chat_agent.cache_clear()

    # Act
    agent = get_chat_agent()
    tools = agent._function_toolset.tools

    # Assert
    for name in ("suggest_recipe", "propose_meal_for_day", "update_user_memory"):
        assert getattr(tools[name].function, "__wrapped__", None) is None
    for name in ("search_recipes", "web_search", "get_daily_weather"):
        assert getattr(tools[name].function, "__wrapped__", None) is not None
    get_chat_agent.cache_clear()


@pytest.mark.asyncio
async def test_given_weather_failure_when_retried_then_recovers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = MagicMock()
    user.id = uuid4()
    preferences = MagicMock()
    preferences.latitude = 42.36
    preferences.longitude = -71.06
    preferences.timezone = "America/New_York"
    preferences.units = "imperial"
    preferences.country = "US"
    preferences.city = "Boston"
    preferences.state_or_region = "MA"
    preferences.postal_code = None
    forecast = {"status": "ok", "provider": "open-meteo", "days": []}
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.random.uniform", lambda _low, _high: 0
    )
    deps = ChatAgentDeps(
        db=cast(AsyncSession, AsyncMock()),
        user=cast(User, user),
        current_datetime=datetime.now(UTC),
        user_timezone="UTC",
    )

    with (
        patch(
            "services.chat_agent.tools.weather.user_preferences_crud.get_by_user_id",
            new_callable=AsyncMock,
            return_value=preferences,
        ),
        patch(
            "services.weather._fetch_open_meteo",
            new_callable=AsyncMock,
            side_effect=[httpx.ReadError("interrupted"), forecast],
        ) as open_meteo,
        patch(
            "services.weather._fetch_weather_gov",
            new_callable=AsyncMock,
            return_value={"status": "error"},
        ) as weather_gov,
    ):
        result = await resilient_read_tool("get_daily_weather", tool_get_daily_weather)(
            _ctx(deps)
        )

    assert result == forecast
    assert open_meteo.await_count == 2
    weather_gov.assert_awaited_once()
    assert "get_daily_weather" in deps.recovered_tools


@pytest.mark.asyncio
async def test_given_transient_web_error_when_searching_then_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    class BrokenClient:
        async def __aenter__(self) -> BrokenClient:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get(self, *_args: object, **_kwargs: object) -> None:
            raise httpx.ConnectError("private URL")

    monkeypatch.setattr("services.web_search._get_api_key", lambda: "test")
    monkeypatch.setattr(
        "services.web_search.httpx.AsyncClient", lambda **_kwargs: BrokenClient()
    )

    # Act and assert
    with pytest.raises(httpx.ConnectError):
        await search_web("chicken")


@pytest.mark.asyncio
async def test_given_unconfigured_web_search_when_called_then_returns_terminal_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("services.web_search._get_api_key", lambda: None)

    result = await tool_web_search(_ctx(_deps(object())), "chicken")

    assert result["status"] == "unconfigured"
    assert result["provider"] == "none"
    assert result["results"] == []


@pytest.mark.asyncio
async def test_given_terminal_web_response_when_called_then_does_not_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests = 0

    class ForbiddenClient:
        async def __aenter__(self) -> ForbiddenClient:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get(self, *_args: object, **_kwargs: object) -> httpx.Response:
            nonlocal requests
            requests += 1
            return httpx.Response(
                403, request=httpx.Request("GET", "https://example.com")
            )

    monkeypatch.setattr("services.web_search._get_api_key", lambda: "test")
    monkeypatch.setattr(
        "services.web_search.httpx.AsyncClient", lambda **_kwargs: ForbiddenClient()
    )

    result = await tool_web_search(_ctx(_deps(object())), "chicken")

    assert result["status"] == "error"
    assert result["results"] == []
    assert requests == 1


@pytest.mark.asyncio
async def test_given_transient_fetch_error_when_tool_runs_then_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    class BrokenExtractor:
        async def fetch_as_markdown(self, _url: str) -> str:
            raise httpx.ConnectError("private URL")

    monkeypatch.setattr(
        "services.chat_agent.tools.web._get_markdown_extractor", BrokenExtractor
    )

    # Act and assert
    with pytest.raises(httpx.ConnectError):
        await tool_fetch_url_as_markdown(_ctx(_deps(object())), "https://example.com/")


@pytest.mark.asyncio
async def test_given_chat_fetch_timeout_when_wrapped_then_retries_typed_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    attempts = 0

    async def timeout_fetch(
        _self: HTMLExtractionService,
        _client: httpx.AsyncClient,
        _url: str,
        _headers: dict[str, str],
    ) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("PRIVATE_UPSTREAM_DETAILS")

    monkeypatch.setattr("services.chat_agent.tools.web._markdown_extractor", None)
    monkeypatch.setattr(
        HTMLExtractionService, "_validate_url", lambda _self, _url: None
    )
    monkeypatch.setattr(
        HTMLExtractionService, "_fetch_with_safe_redirects", timeout_fetch
    )
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.random.uniform", lambda _low, _high: 0
    )

    # Act
    result = await resilient_read_tool(
        "fetch_url_as_markdown", tool_fetch_url_as_markdown
    )(_ctx(_deps(object())), "https://example.com/slow")

    # Assert
    assert attempts == MAX_ATTEMPTS
    assert result == failure_result(
        "transient_network_error", tool_name="fetch_url_as_markdown"
    )
    assert "PRIVATE_UPSTREAM_DETAILS" not in str(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("both_fail", [False, True])
async def test_given_parallel_failure_when_model_continues_then_keeps_results(
    both_fail: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.random.uniform", lambda _low, _high: 0
    )

    def model(messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        returned = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if not returned:
            return ModelResponse(
                parts=[
                    ToolCallPart("good", {}, tool_call_id="good-1"),
                    ToolCallPart("bad", {}, tool_call_id="bad-1"),
                ]
            )
        return ModelResponse(
            parts=[
                TextPart(
                    "Please retry." if both_fail else "Here is the available result."
                )
            ]
        )

    async def good(_ctx: RunContext[ChatAgentDeps]) -> dict[str, str]:
        """Get the available result."""
        if both_fail:
            raise httpx.ConnectError("private")
        return {"value": "available"}

    async def bad(_ctx: RunContext[ChatAgentDeps]) -> dict[str, str]:
        """Get an unavailable result."""
        raise httpx.ConnectError("private")

    agent = Agent(FunctionModel(model), deps_type=ChatAgentDeps, output_type=str)
    agent.tool(name="good")(resilient_read_tool("good", good))
    agent.tool(name="bad")(resilient_read_tool("bad", bad))
    # Act
    output = await agent.run("Look up recipes", deps=_deps(object()))
    results = [
        part
        for message in output.all_messages()
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    ]

    # Assert
    assert len(results) == 2
    bad_result = next(part for part in results if part.tool_call_id == "bad-1")
    assert bad_result.content == failure_result("transient_network_error")
    good_result = next(part for part in results if part.tool_call_id == "good-1")
    assert good_result.content == (
        failure_result("transient_network_error")
        if both_fail
        else {"value": "available"}
    )
    assert output.output == (
        "Please retry." if both_fail else "Here is the available result."
    )


@pytest.mark.asyncio
async def test_given_exhausted_tool_when_model_repeats_then_stops_dependency_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setattr(
        "services.chat_agent.tool_recovery.random.uniform", lambda _low, _high: 0
    )
    attempts = 0

    async def lookup(_ctx: RunContext[ChatAgentDeps]) -> dict[str, str | bool]:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("private")

    wrapped = resilient_read_tool("lookup", lookup)
    context = _ctx(_deps(object()))

    # Act
    outcomes = [await wrapped(context) for _ in range(4)]

    # Assert
    assert attempts == 3 * MAX_ATTEMPTS
    assert all(isinstance(outcome, dict) for outcome in outcomes)
    assert [outcome["error_code"] for outcome in outcomes] == [
        "transient_network_error",
        "transient_network_error",
        "transient_network_error",
        "tool_unavailable",
    ]
    assert outcomes[-1]["retryable"] is False


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (ValueError("bad request"), None),
        (OperationalError("query", {}, Exception("bad SQL")), None),
        (
            OperationalError(
                "query", {}, Exception("bad SQL"), connection_invalidated=True
            ),
            "transient_database_error",
        ),
        (httpx.ConnectError("network"), "transient_network_error"),
        (httpx.ReadError("interrupted"), "transient_network_error"),
        (httpx.WriteError("interrupted"), "transient_network_error"),
        (httpx.CloseError("interrupted"), "transient_network_error"),
        (httpx.RemoteProtocolError("disconnected"), "transient_network_error"),
        (httpx.LocalProtocolError("invalid request"), None),
        (httpx.InvalidURL("invalid URL"), None),
        (genai_errors.ClientError(429, {}), "transient_service_error"),
        (genai_errors.ClientError(400, {}), None),
        (genai_errors.ServerError(503, {}), "transient_service_error"),
        (genai_errors.ServerError(501, {}), None),
        (
            httpx.HTTPStatusError(
                "service",
                request=httpx.Request("GET", "https://test"),
                response=httpx.Response(503),
            ),
            "transient_service_error",
        ),
        (
            httpx.HTTPStatusError(
                "auth",
                request=httpx.Request("GET", "https://test"),
                response=httpx.Response(403),
            ),
            None,
        ),
    ],
)
def test_given_typed_exception_when_classified_then_only_transient_is_retryable(
    exception: Exception, expected: str | None
) -> None:
    assert classify_tool_error(exception) == expected
