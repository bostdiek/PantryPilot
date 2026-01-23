"""Unit tests for chat datetime context resolution."""

from __future__ import annotations

from datetime import UTC, datetime

from api.v1.chat import _resolve_current_datetime


def test_resolve_current_datetime_uses_server_now_when_missing() -> None:
    server_now = datetime(2026, 1, 23, 15, 0, 0, tzinfo=UTC)
    assert _resolve_current_datetime(None, server_now=server_now) == server_now


def test_resolve_current_datetime_uses_server_now_when_invalid() -> None:
    server_now = datetime(2026, 1, 23, 15, 0, 0, tzinfo=UTC)
    resolved = _resolve_current_datetime("not-a-datetime", server_now=server_now)
    assert resolved == server_now


def test_resolve_current_datetime_accepts_reasonable_client_time() -> None:
    server_now = datetime(2026, 1, 23, 15, 0, 0, tzinfo=UTC)
    # Within skew window
    client_dt = "2026-01-23T14:30:00Z"
    resolved = _resolve_current_datetime(client_dt, server_now=server_now)
    assert resolved == datetime(2026, 1, 23, 14, 30, 0, tzinfo=UTC)


def test_resolve_current_datetime_ignores_large_skew() -> None:
    server_now = datetime(2026, 1, 23, 15, 0, 0, tzinfo=UTC)
    client_dt = "2024-05-15T10:53:00Z"
    assert _resolve_current_datetime(client_dt, server_now=server_now) == server_now
