"""Domain exceptions for AI extraction pipeline (Phase 3 scaffold).

These exceptions provide a taxonomy for deterministic error handling across
HTML fetching, agent execution, conversion, and draft persistence. The API
layer (and streaming orchestrator) will map them to HTTP / SSE forms.

Initially these are *not yet* raised by components; they serve as a contract
for subsequent refactors so callers can replace generic Exception handling
with explicit branches. Each exception carries a stable `error_code` property
for analytics / metrics tagging.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AIExtractionError(Exception):
    """Base class for AI extraction domain errors."""

    message: str
    error_code: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.error_code}: {self.message}"


class HTMLFetchError(AIExtractionError):
    def __init__(self, message: str = "Failed to fetch or sanitize HTML") -> None:
        super().__init__(message=message, error_code="fetch_failed")


class HTMLValidationError(AIExtractionError):
    def __init__(self, message: str = "Fetched HTML invalid or empty") -> None:
        super().__init__(message=message, error_code="empty_html")


class AgentFailure(AIExtractionError):
    def __init__(self, message: str = "AI agent execution failed") -> None:
        super().__init__(message=message, error_code="agent_error")


class RecipeNotFound(AIExtractionError):
    def __init__(self, message: str = "No recipe found in page content") -> None:
        super().__init__(message=message, error_code="not_found")


class ConversionError(AIExtractionError):
    def __init__(
        self,
        message: str = "Failed to convert extraction result to recipe schema",
    ) -> None:
        super().__init__(message=message, error_code="convert_failed")
