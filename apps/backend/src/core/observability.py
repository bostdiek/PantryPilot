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
- Set OTEL_TRACES_EXPORTER=console locally to print spans without Azure secrets

For production (Azure):
- Set APPLICATIONINSIGHTS_CONNECTION_STRING to your App Insights connection string
- Traces, metrics, and logs will be exported to Azure Monitor
- Use Azure Monitor workspaces for retention and compliance
"""

from __future__ import annotations

import importlib.metadata as importlib_metadata
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from enum import StrEnum
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from core.error_handler import get_correlation_id


if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Environment variable names
_ENV_ENABLE_OBSERVABILITY = "ENABLE_OBSERVABILITY"
_ENV_APP_INSIGHTS_CONN_STRING = "APPLICATIONINSIGHTS_CONNECTION_STRING"
_ENV_OTEL_SERVICE_NAME = "OTEL_SERVICE_NAME"
_ENV_OTEL_TRACES_EXPORTER = "OTEL_TRACES_EXPORTER"

# Default service name for OpenTelemetry
_DEFAULT_SERVICE_NAME = "pantrypilot-backend"

# Paths to exclude from automatic tracing (reduce noise for health checks)
EXCLUDED_URLS = "health,health/,favicon.ico"

_pydantic_ai_instrumented = False


class ProductTelemetryEventName(StrEnum):
    """Canonical backend product telemetry event names."""

    ASSISTANT_MESSAGE_STARTED = "assistant_message_started"
    ASSISTANT_MESSAGE_COMPLETED = "assistant_message_completed"
    ASSISTANT_MESSAGE_FAILED = "assistant_message_failed"
    ASSISTANT_TOOL_STARTED = "assistant_tool_started"
    ASSISTANT_TOOL_COMPLETED = "assistant_tool_completed"
    URL_IMPORT_STARTED = "url_import_started"
    URL_IMPORT_STREAM_FALLBACK = "url_import_stream_fallback"
    URL_IMPORT_COMPLETED = "url_import_completed"
    URL_IMPORT_FAILED = "url_import_failed"
    IMAGE_IMPORT_STARTED = "image_import_started"
    IMAGE_IMPORT_COMPLETED = "image_import_completed"
    IMAGE_IMPORT_FAILED = "image_import_failed"
    RECIPE_SEARCH_SUBMITTED = "recipe_search_submitted"
    RECIPE_SEARCH_RESULT_CLICKED = "recipe_search_result_clicked"


def _safe_telemetry_value(value: object) -> bool | float | int | str:
    """Normalize telemetry values to OpenTelemetry-friendly scalar primitives."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float | str):
        return value
    return str(value)


def build_product_telemetry_attributes(
    *,
    event: ProductTelemetryEventName,
    feature_name: str,
    request_id: str | None = None,
    conversation_id: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
    success: bool | None = None,
    latency_ms: int | None = None,
    error_type: str | None = None,
    tool_count: int | None = None,
    tool_names: list[str] | None = None,
    streamed: bool | None = None,
    cancelled: bool | None = None,
) -> dict[str, bool | float | int | str]:
    """Build a bounded metadata-only product telemetry attribute payload."""
    attrs: dict[str, bool | float | int | str] = {
        "product.telemetry.event": event.value,
        "product.telemetry.feature_name": feature_name,
        "product.telemetry.request_id": request_id or get_correlation_id(),
    }

    optional: dict[str, object | None] = {
        "product.telemetry.conversation_id": conversation_id,
        "product.telemetry.provider": provider,
        "product.telemetry.model_name": model_name,
        "product.telemetry.success": success,
        "product.telemetry.latency_ms": latency_ms,
        "product.telemetry.error_type": error_type,
        "product.telemetry.tool_count": tool_count,
        "product.telemetry.streamed": streamed,
        "product.telemetry.cancelled": cancelled,
    }

    for key, value in optional.items():
        if value is not None:
            attrs[key] = _safe_telemetry_value(value)

    if tool_names:
        attrs["product.telemetry.tool_names"] = ",".join(tool_names)

    return attrs


def record_product_telemetry_event(
    span: Any,
    *,
    event: ProductTelemetryEventName,
    feature_name: str,
    request_id: str | None = None,
    conversation_id: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
    success: bool | None = None,
    latency_ms: int | None = None,
    error_type: str | None = None,
    tool_count: int | None = None,
    tool_names: list[str] | None = None,
    streamed: bool | None = None,
    cancelled: bool | None = None,
) -> dict[str, bool | float | int | str]:
    """Attach product telemetry metadata to a span and emit a lifecycle event.

    The lifecycle event name is recorded via ``span.add_event(...)`` so multiple
    events can be attached to the same span without later writes overwriting the
    original ``product.telemetry.event`` value.
    """
    attrs = build_product_telemetry_attributes(
        event=event,
        feature_name=feature_name,
        request_id=request_id,
        conversation_id=conversation_id,
        provider=provider,
        model_name=model_name,
        success=success,
        latency_ms=latency_ms,
        error_type=error_type,
        tool_count=tool_count,
        tool_names=tool_names,
        streamed=streamed,
        cancelled=cancelled,
    )

    for key, value in attrs.items():
        if key == "product.telemetry.event":
            continue
        span.set_attribute(key, value)

    span.add_event(event.value, attributes=attrs)
    return attrs


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


def _is_console_trace_exporter_enabled() -> bool:
    """Return whether local console span export is requested."""
    exporters = {
        exporter.strip().lower()
        for exporter in os.getenv(_ENV_OTEL_TRACES_EXPORTER, "").split(",")
    }
    return "console" in exporters


def _get_installed_version(package_name: str) -> str:
    """Return installed package version for observability diagnostics."""
    try:
        return importlib_metadata.version(package_name)
    except importlib_metadata.PackageNotFoundError:
        return "not-installed"


def _enable_pydantic_ai_instrumentation() -> None:
    """Enable Pydantic AI OpenTelemetry spans after provider setup."""
    global _pydantic_ai_instrumented

    if _pydantic_ai_instrumented:
        logger.debug("Pydantic AI OpenTelemetry instrumentation already enabled")
        return

    try:
        from pydantic_ai import Agent

        Agent.instrument_all()
        _pydantic_ai_instrumented = True
        logger.info("Pydantic AI OpenTelemetry instrumentation enabled")
    except ImportError as exc:
        logger.warning(
            "Pydantic AI instrumentation unavailable: %s. Installed version: %s",
            exc,
            _get_installed_version("pydantic-ai-slim"),
        )
    except Exception as exc:
        logger.exception(
            "Failed to enable Pydantic AI OpenTelemetry instrumentation: %s",
            exc,
        )


def _configure_console_trace_exporter(service_name: str) -> None:
    """Configure local console trace export for development validation."""
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor().instrument(excluded_urls=EXCLUDED_URLS)


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

    service_name = os.getenv(_ENV_OTEL_SERVICE_NAME, _DEFAULT_SERVICE_NAME)
    connection_string = _get_connection_string()

    # Set excluded URLs for FastAPI instrumentation before either Azure Monitor
    # or the local development exporter configures instrumentation.
    os.environ.setdefault("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS", EXCLUDED_URLS)

    if not connection_string and _is_console_trace_exporter_enabled():
        try:
            _configure_console_trace_exporter(service_name)
            _enable_pydantic_ai_instrumentation()
            logger.info(
                "Console OpenTelemetry observability configured for service '%s'",
                service_name,
            )
            return True
        except ImportError as exc:
            logger.warning(
                "Failed to import OpenTelemetry console exporter dependencies: %s",
                exc,
            )
            return False
        except Exception as exc:
            logger.exception(
                "Failed to configure console OpenTelemetry observability: %s",
                exc,
            )
            return False

    if not connection_string:
        logger.warning(
            "Observability enabled but %s not set and %s is not console. "
            "Skipping OpenTelemetry setup.",
            _ENV_APP_INSIGHTS_CONN_STRING,
            _ENV_OTEL_TRACES_EXPORTER,
        )
        return False

    try:
        # Import Azure Monitor OpenTelemetry only when needed
        from azure.monitor.opentelemetry import configure_azure_monitor

        # Configure Azure Monitor with FastAPI instrumentation
        # Note: This must be called BEFORE importing FastAPI for proper instrumentation
        configure_azure_monitor(
            connection_string=connection_string,
            # Exclude health check endpoints from tracing to reduce noise
            # FastAPI instrumentation reads this from environment
            # We set it here for documentation purposes; the actual exclusion
            # is handled by setting OTEL_PYTHON_FASTAPI_EXCLUDED_URLS env var
        )

        _enable_pydantic_ai_instrumentation()

        logger.info(
            "Azure Monitor observability configured for service '%s'",
            service_name,
        )
        return True

    except ImportError as exc:
        installed_versions = {
            "azure-monitor-opentelemetry": _get_installed_version(
                "azure-monitor-opentelemetry"
            ),
            "azure-monitor-opentelemetry-exporter": _get_installed_version(
                "azure-monitor-opentelemetry-exporter"
            ),
            "opentelemetry-api": _get_installed_version("opentelemetry-api"),
            "opentelemetry-sdk": _get_installed_version("opentelemetry-sdk"),
        }
        logger.warning(
            "Failed to import Azure Monitor OpenTelemetry dependencies: %s. "
            "Installed versions: %s. Ensure compatible opentelemetry-* versions "
            "are installed (known-safe range for this app is <1.39).",
            exc,
            installed_versions,
        )
        return False
    except Exception as e:
        logger.exception("Failed to configure Azure Monitor observability: %s", e)
        return False


def get_tracer(name: str) -> Any:
    """Get an OpenTelemetry tracer for custom instrumentation.

    Use this to create custom spans for operations that aren't automatically
    instrumented (e.g., LLM calls, custom business logic).

    Args:
        name: The name of the tracer, typically __name__ of the calling module.

    Returns:
        An OpenTelemetry Tracer instance when OpenTelemetry is available and
        properly configured. Returns a no-op tracer (_NoOpTracer) when
        OpenTelemetry is not installed or observability is disabled. The no-op
        tracer provides the same interface but doesn't emit any spans.

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

        return trace.get_tracer(name)
    except ImportError:
        # Return a no-op tracer if OpenTelemetry is not installed
        logger.debug("OpenTelemetry not available; returning no-op tracer")
        return _NoOpTracer()


def get_current_span() -> Any:
    """Return the active OpenTelemetry span or a no-op span."""
    try:
        from opentelemetry import trace

        return trace.get_current_span()
    except ImportError:
        logger.debug("OpenTelemetry not available; returning no-op current span")
        return _NoOpSpan()


def set_span_error_status(span: Any, exception: BaseException) -> None:
    """Set OpenTelemetry error status with a low-cardinality description."""
    try:
        from opentelemetry.trace import Status, StatusCode

        span.set_status(Status(StatusCode.ERROR, type(exception).__name__))
    except ImportError:
        logger.debug("OpenTelemetry not available; skipping span status")


class _NoOpTracer:
    """A no-op tracer for when OpenTelemetry is not available."""

    @contextmanager
    def start_as_current_span(self, name: str, **kwargs: object) -> Iterator[_NoOpSpan]:
        """Return a no-op context manager."""
        yield _NoOpSpan()

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

    def set_status(self, status: object) -> None:
        """No-op status setter."""

    def end(self) -> None:
        """No-op span end."""
