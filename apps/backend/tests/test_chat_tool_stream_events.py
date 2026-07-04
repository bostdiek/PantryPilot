"""Unit tests for tool lifecycle event handling in chat streaming."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.chat import _handle_agent_stream_event, _ToolCallStart
from models.chat_tool_calls import ChatToolCall


class _FakeSpan:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object] | None]] = []

    def add_event(
        self,
        name: str,
        attributes: dict[str, object] | None = None,
    ) -> None:
        self.events.append((name, attributes))


class _FakeDb:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits: int = 0

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1


@pytest.mark.asyncio
async def test_handle_agent_stream_event_emits_tool_started_and_result() -> None:
    from pydantic_ai.messages import (
        FunctionToolCallEvent,
        FunctionToolResultEvent,
        ToolCallPart,
        ToolReturnPart,
    )

    conversation_id = uuid4()
    message_id = uuid4()
    user_id = uuid4()

    db = _FakeDb()
    tool_calls_by_id: dict[str, _ToolCallStart] = {}
    tool_call_order = [0]

    call_part = ToolCallPart(
        tool_name="get_daily_weather",
        args={"zip": "12345"},
        tool_call_id="call_1",
    )
    call_event = FunctionToolCallEvent(call_part)

    sse_started, output_started, blocks_started = await _handle_agent_stream_event(
        call_event,
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=user_id,
        db=cast(AsyncSession, db),
        tool_calls_by_id=tool_calls_by_id,
        tool_call_order=tool_call_order,
        request_id="req-1",
    )

    assert output_started is None
    assert blocks_started == []
    assert len(sse_started) > 0
    sse_started_str = "".join(sse_started)
    assert '"event":"tool.started"' in sse_started_str
    assert '"tool_call_id":"call_1"' in sse_started_str

    result_part = ToolReturnPart(
        tool_name="get_daily_weather",
        content={"temp": 72},
        tool_call_id="call_1",
    )
    result_event = FunctionToolResultEvent(result_part)

    sse_result, output_result, blocks_result = await _handle_agent_stream_event(
        result_event,
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=user_id,
        db=cast(AsyncSession, db),
        tool_calls_by_id=tool_calls_by_id,
        tool_call_order=tool_call_order,
        request_id="req-1",
    )

    assert output_result is None
    assert blocks_result == []
    assert len(sse_result) > 0
    sse_result_str = "".join(sse_result)
    assert '"event":"tool.result"' in sse_result_str
    assert '"tool_call_id":"call_1"' in sse_result_str
    assert '"status":"success"' in sse_result_str

    persisted = [obj for obj in db.added if isinstance(obj, ChatToolCall)]
    assert len(persisted) == 1
    assert persisted[0].message_id == message_id
    assert persisted[0].tool_name == "get_daily_weather"
    assert persisted[0].arguments == {"zip": "12345"}
    assert persisted[0].result == {"temp": 72}
    assert persisted[0].status == "success"
    assert db.commits == 1


@pytest.mark.asyncio
async def test_handle_agent_stream_event_records_tool_lifecycle_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic_ai.messages import (
        FunctionToolCallEvent,
        FunctionToolResultEvent,
        ToolCallPart,
        ToolReturnPart,
    )

    conversation_id = uuid4()
    message_id = uuid4()
    user_id = uuid4()
    span = _FakeSpan()
    db = _FakeDb()
    tool_calls_by_id: dict[str, _ToolCallStart] = {}
    tool_call_order = [0]

    monkeypatch.setattr("api.v1.chat.get_current_span", lambda: span)

    call_event = FunctionToolCallEvent(
        ToolCallPart(
            tool_name="get_daily_weather",
            args={"zip": "12345"},
            tool_call_id="call_1",
        )
    )
    await _handle_agent_stream_event(
        call_event,
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=user_id,
        db=cast(AsyncSession, db),
        tool_calls_by_id=tool_calls_by_id,
        tool_call_order=tool_call_order,
        request_id="req-1",
    )

    result_event = FunctionToolResultEvent(
        ToolReturnPart(
            tool_name="get_daily_weather",
            content={"temp": 72},
            tool_call_id="call_1",
        )
    )
    await _handle_agent_stream_event(
        result_event,
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=user_id,
        db=cast(AsyncSession, db),
        tool_calls_by_id=tool_calls_by_id,
        tool_call_order=tool_call_order,
        request_id="req-1",
    )

    assert [event_name for event_name, _attrs in span.events] == [
        "assistant_tool_started",
        "assistant_tool_completed",
    ]
    started_attrs = span.events[0][1] or {}
    completed_attrs = span.events[1][1] or {}
    assert started_attrs["product.telemetry.tool_names"] == "get_daily_weather"
    assert completed_attrs["product.telemetry.success"] is True
    assert "product.telemetry.latency_ms" in completed_attrs
    assert "tool_call_id" not in started_attrs
    assert "tool_call_id" not in completed_attrs


def test_extract_tool_name_logs_warning_on_unknown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from api.v1.chat import _extract_tool_name

    class _Part:
        pass

    with caplog.at_level("WARNING"):
        name = _extract_tool_name(_Part())

    assert name == "unknown"
    assert any("Tool name extraction failed" in msg for msg in caplog.messages)
