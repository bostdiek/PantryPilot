"""Typed classification of transient read-only dependency errors."""

from __future__ import annotations

import asyncio

import asyncpg  # type: ignore[import-untyped]
import httpx
import openai
from google.genai import errors as genai_errors
from sqlalchemy.exc import DBAPIError, TimeoutError as SQLAlchemyTimeoutError


RETRYABLE_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}


def _is_transient_database_error(exc: DBAPIError) -> bool:
    if exc.connection_invalidated:
        return True
    original = exc.orig
    if isinstance(original, asyncpg.PostgresConnectionError):
        return True
    sqlstate = getattr(original, "sqlstate", None)
    return isinstance(sqlstate, str) and (
        sqlstate.startswith("08") or sqlstate in {"40001", "40P01", "53300", "57P03"}
    )


def classify_tool_error(exc: Exception) -> str | None:
    """Identify transient dependency errors without inspecting error messages."""
    if isinstance(exc, DBAPIError) and _is_transient_database_error(exc):
        return "transient_database_error"
    if isinstance(exc, asyncpg.PostgresConnectionError):
        return "transient_database_error"
    if isinstance(exc, SQLAlchemyTimeoutError):
        return "transient_database_error"
    if isinstance(
        exc,
        asyncio.TimeoutError
        | httpx.TimeoutException
        | httpx.NetworkError
        | httpx.RemoteProtocolError,
    ):
        return "transient_network_error"
    if isinstance(exc, httpx.HTTPStatusError):
        return (
            "transient_service_error"
            if exc.response.status_code in RETRYABLE_HTTP_STATUSES
            else None
        )
    if isinstance(exc, openai.APIConnectionError):
        return "transient_network_error"
    if isinstance(exc, openai.APIStatusError):
        return (
            "transient_service_error"
            if exc.status_code in RETRYABLE_HTTP_STATUSES
            else None
        )
    if isinstance(exc, genai_errors.ClientError | genai_errors.ServerError):
        return (
            "transient_service_error" if exc.code in RETRYABLE_HTTP_STATUSES else None
        )
    return None
