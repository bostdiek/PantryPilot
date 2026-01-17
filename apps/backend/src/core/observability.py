"""Observability configuration for Azure Monitor and OpenTelemetry.

This module provides centralized observability setup for the PantryPilot backend,
integrating with Azure Monitor Application Insights via OpenTelemetry.

IMPORTANT: Call configure_observability() at the very start of application
initialization (before importing FastAPI or other instrumented packages) to
ensure proper instrumentation of all HTTP requests, database calls, and other
telemetry sources.

PII and Sensitive Data Guidance:
--------------------------------
- NEVER log raw user messages, recipe content, or personal data in span attributes
- Use correlation IDs to link traces without embedding sensitive content
- Prefer structured logging with the project's StructuredLogger (core/error_handler.py)
  which automatically redacts sensitive keys
- Logfire scrubbing only applies to structured fields, NOT span/log messages themselves
- When adding custom spans, avoid including:
  * User email addresses, names, or profile information
  * API keys, tokens, or credentials
  * Recipe content or ingredient lists that may contain personal preferences
  * Location data beyond city-level granularity
  * Tool call arguments that may contain user-provided content

For local development:
- Logfire can be used as optional dev tooling for quick trace visualization
- Do NOT rely on Logfire for production retention
- Set ENABLE_OBSERVABILITY=false locally if traces are not needed

For production (Azure):
- Set APPLICATIONINSIGHTS_CONNECTION_STRING to your App Insights connection string
- Traces, metrics, and logs will be exported to Azure Monitor
- Use Azure Monitor workspaces for retention and compliance
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Environment variable names
_ENV_ENABLE_OBSERVABILITY = "ENABLE_OBSERVABILITY"
_ENV_APP_INSIGHTS_CONN_STRING = "APPLICATIONINSIGHTS_CONNECTION_STRING"
_ENV_OTEL_SERVICE_NAME = "OTEL_SERVICE_NAME"

# Default service name for OpenTelemetry
_DEFAULT_SERVICE_NAME = "pantrypilot-backend"

# Paths to exclude from automatic tracing (reduce noise for health checks)
EXCLUDED_URLS = "health,health/,favicon.ico"


def _is_observability_enabled() -> bool:
    """Check if observability is enabled via environment variable.

    Returns True if ENABLE_OBSERVABILITY is set to a truthy value
    (e.g., "true", "1", "yes"). Defaults to False if not set.
    """
    value = os.getenv(_ENV_ENABLE_OBSERVABILITY, "false").lower()
    return value in {"true", "1", "yes", "on"}


def _get_connection_string() -> str | None:
    """Get the Application Insights connection string from environment."""
    return os.getenv(_ENV_APP_INSIGHTS_CONN_STRING)


@lru_cache
def configure_observability() -> bool:
    """Configure OpenTelemetry with Azure Monitor for production observability.

    This function should be called once at application startup, BEFORE importing
    FastAPI or other packages that should be instrumented.

    Returns:
        True if observability was configured successfully, False otherwise.

    Environment Variables:
        ENABLE_OBSERVABILITY: Set to "true" to enable (default: "false")
        APPLICATIONINSIGHTS_CONNECTION_STRING: Azure Monitor connection string
        OTEL_SERVICE_NAME: Service name for traces (default: "pantrypilot-backend")

    Example:
        # In main.py, at the very top:
        from core.observability import configure_observability
        configure_observability()

        # Then import FastAPI
        from fastapi import FastAPI
    """
    if not _is_observability_enabled():
        logger.info(
            "Observability disabled. Set %s=true to enable Azure Monitor.",
            _ENV_ENABLE_OBSERVABILITY,
        )
        return False

    connection_string = _get_connection_string()
    if not connection_string:
        logger.warning(
            "Observability enabled but %s not set. Skipping Azure Monitor setup.",
            _ENV_APP_INSIGHTS_CONN_STRING,
        )
        return False

    try:
        # Import Azure Monitor OpenTelemetry only when needed
        from azure.monitor.opentelemetry import configure_azure_monitor

        # Set service name for OpenTelemetry resource attributes
        service_name = os.getenv(_ENV_OTEL_SERVICE_NAME, _DEFAULT_SERVICE_NAME)

        # Configure Azure Monitor with FastAPI instrumentation
        # Note: This must be called BEFORE importing FastAPI for proper instrumentation
        configure_azure_monitor(
            connection_string=connection_string,
            # Exclude health check endpoints from tracing to reduce noise
            # FastAPI instrumentation reads this from environment
            # We set it here for documentation purposes; the actual exclusion
            # is handled by setting OTEL_PYTHON_FASTAPI_EXCLUDED_URLS env var
        )

        # Set excluded URLs for FastAPI instrumentation
        os.environ.setdefault("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS", EXCLUDED_URLS)

        logger.info(
            "Azure Monitor observability configured for service '%s'",
            service_name,
        )
        return True

    except ImportError:
        logger.warning(
            "azure-monitor-opentelemetry package not installed. "
            "Install with: uv add azure-monitor-opentelemetry"
        )
        return False
    except Exception as e:
        logger.exception("Failed to configure Azure Monitor observability: %s", e)
        return False


def get_tracer(name: str) -> _NoOpTracer:
    """Get an OpenTelemetry tracer for custom instrumentation.

    Use this to create custom spans for operations that aren't automatically
    instrumented (e.g., LLM calls, custom business logic).

    Args:
        name: The name of the tracer, typically __name__ of the calling module.

    Returns:
        An OpenTelemetry Tracer instance. If observability is not configured,
        returns a no-op tracer that doesn't emit spans.

    Example:
        from core.observability import get_tracer

        tracer = get_tracer(__name__)

        async def process_chat_message(message: str) -> str:
            with tracer.start_as_current_span("process_chat_message") as span:
                # Add safe attributes (no PII!)
                span.set_attribute("message.length", len(message))
                # Do processing...
                return result

    WARNING: Never add user content or PII to span attributes!
    """
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)  # type: ignore[return-value]
    except ImportError:
        # Return a no-op tracer if OpenTelemetry is not installed
        logger.debug("OpenTelemetry not available; returning no-op tracer")
        return _NoOpTracer()


class _NoOpTracer:
    """A no-op tracer for when OpenTelemetry is not available."""

    def start_as_current_span(self, name: str, **kwargs: object) -> _NoOpSpan:
        """Return a no-op context manager."""
        return _NoOpSpan()

    def start_span(self, name: str, **kwargs: object) -> _NoOpSpan:
        """Return a no-op span."""
        return _NoOpSpan()


class _NoOpSpan:
    """A no-op span for when OpenTelemetry is not available."""

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def set_attribute(self, key: str, value: object) -> None:
        """No-op attribute setter."""

    def add_event(self, name: str, attributes: dict[str, object] | None = None) -> None:
        """No-op event adder."""

    def record_exception(self, exception: BaseException) -> None:
        """No-op exception recorder."""

    def end(self) -> None:
        """No-op span end."""
