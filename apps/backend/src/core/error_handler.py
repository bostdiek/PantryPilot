"""Centralized error handling and logging for PantryPilot API.

This module provides:
- Global exception handler for FastAPI
- Structured logging with correlation IDs
- Environment-aware error responses (generic in production, detailed in dev)
- Prevention of sensitive data leakage
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from core.config import get_settings
from core.exceptions import DuplicateUserError, UserNotFoundError
from core.security_config import get_allowed_error_fields, is_sensitive_key
from schemas.api import ErrorResponse


# Note: sensitive keys are centralized in `core.security_config.SENSITIVE_KEYS` and
# exposed via `is_sensitive_key`. Avoid duplicating that list here to prevent
# drift and keep a single source of truth for redaction rules.

# Context variable for correlation ID tracking across async calls
_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Configure structured logging
logger = logging.getLogger(__name__)

# Error type mappings for consistent responses
ERROR_TYPE_MESSAGES = {
    DuplicateUserError: "The requested resource already exists",
    UserNotFoundError: "The requested resource was not found",
    ValidationError: "Invalid request data provided",
    IntegrityError: "A data integrity constraint was violated",
}


def get_correlation_id() -> str:
    """Get or create a correlation ID for request tracing."""
    # _correlation_id_var may hold Optional[str]
    correlation_id: str | None = _correlation_id_var.get()
    if correlation_id is None or correlation_id == "":
        new_id = str(uuid.uuid4())
        _correlation_id_var.set(new_id)
        return new_id
    return correlation_id


def set_correlation_id(correlation_id: str | None) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id_var.set(correlation_id)


class StructuredLogger:
    """Structured logger that includes correlation IDs and sanitized data."""

    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)

    def _log_with_context(
        self,
        level: int,
        message: str,
        extra_data: dict[str, Any] | None = None,
        exc_info: bool = False,
    ) -> None:
        """Log with correlation ID and structured data."""
        correlation_id = get_correlation_id()

        # Sanitize extra data to prevent PII leakage
        sanitized_data = self._sanitize_data(extra_data or {})

        # Create structured log entry
        log_data = {
            "correlation_id": correlation_id,
            "message": message,
            **sanitized_data,
        }

        # Use proper JSON encoding for structured logs
        settings = get_settings()
        if settings.ENVIRONMENT == "production":
            # In production, pass the structured data via the `extra` argument so the
            # JSONFormatter in `setup_logging()` can incorporate it without
            # double-encoding. This keeps the final log a valid JSON object.
            try:
                self.logger.log(
                    level,
                    message,
                    extra={"structured_data": log_data},
                    exc_info=exc_info,
                )
            except Exception as e:
                # Fallback if logging with extra fails for any reason
                fallback_message = f"[{correlation_id}] {message} (logging failed: {e})"
                # Ensure we still write something informative to logs
                self.logger.log(level, fallback_message, exc_info=exc_info)
        else:
            # In development, use human-readable format
            self.logger.log(
                level,
                f"[{correlation_id}] {message}",
                extra={"structured_data": log_data},
                exc_info=exc_info,
            )

    def _sanitize_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove or mask sensitive data from log entries."""
        sanitized: dict[str, Any] = {}

        # Fast-paths reduce overall complexity: non-dict or empty dict
        if not isinstance(data, dict) or not data:
            return {} if not isinstance(data, dict) else {}

        header_redaction = self._redact_header_like(data)
        if header_redaction is not None:
            return header_redaction

        for key, value in data.items():
            if is_sensitive_key(key):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = self._sanitize_value(value)

        return sanitized

    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize a single value which may be a dict, list, or primitive."""
        if isinstance(value, dict):
            # Recurse into dicts
            return self._sanitize_data(value)
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        # Primitive value: return as-is
        return value

    def _redact_header_like(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """If `data` is a header-like dict, return a redacted version or None.

        A header-like dict has keys like `name`/`key` and `value`. If the name/key
        is considered sensitive, its value is redacted.
        """
        # `data` is annotated as a dict in the signature, so this runtime
        # check is unreachable and confuses static type checkers (mypy).
        # Remove the redundant check to keep mypy happy.

        if not (
            ("name" in data and "value" in data) or ("key" in data and "value" in data)
        ):
            return None

        header_name = data.get("name") or data.get("key")
        if not isinstance(header_name, str) or not is_sensitive_key(header_name):
            return None

        redacted: dict[str, Any] = {}
        for sub_k, sub_v in data.items():
            if sub_k.lower() in {"value", "val", "v"}:
                redacted[sub_k] = "[REDACTED]"
            elif isinstance(sub_v, dict):
                redacted[sub_k] = self._sanitize_data(sub_v)
            else:
                redacted[sub_k] = "[REDACTED]" if is_sensitive_key(sub_k) else sub_v

        return redacted

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info level message."""
        self._log_with_context(logging.INFO, message, kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning level message."""
        self._log_with_context(logging.WARNING, message, kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error level message."""
        self._log_with_context(logging.ERROR, message, kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._log_with_context(logging.ERROR, message, kwargs, exc_info=True)


# Global structured logger instance
structured_logger = StructuredLogger(__name__)


class ExceptionNormalizationMiddleware(BaseHTTPMiddleware):
    """Catch any uncaught Exception and delegate to global_exception_handler.

    This avoids touching private middleware_stack internals and guarantees
    a final safety net consistent with centralized error handling.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001
            return await global_exception_handler(request, exc)


def _build_error_response(
    *,
    correlation_id: str,
    error_type: str,
    message: str,
    environment: str,
    details: dict[str, Any] | None = None,
    traceback_str: str | None = None,
    exception_type: str | None = None,
    validation_errors: Any | None = None,
    status_code: int = 500,
) -> JSONResponse:
    """Construct a sanitized JSON error response respecting environment rules."""
    allowed_fields = get_allowed_error_fields(environment)

    error_body: dict[str, Any] = {
        "correlation_id": correlation_id,
        "type": error_type,
    }

    # Only include optional fields if allowed in this environment
    if "details" in allowed_fields and details:
        error_body["details"] = details
    if "traceback" in allowed_fields and traceback_str:
        error_body["traceback"] = traceback_str
    if "exception_type" in allowed_fields and exception_type:
        error_body["exception_type"] = exception_type
    if "validation_errors" in allowed_fields and validation_errors is not None:
        error_body["validation_errors"] = validation_errors

    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            message=message,
            error=error_body,
            success=False,
        ).model_dump(),
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler providing structured, sanitized responses.

    This function centralizes all error handling to ensure:
    - Consistent JSON error envelope
    - Correlation ID is always present
    - Sensitive data is never leaked (production)
    - Helpful diagnostics in development
    """
    settings = get_settings()
    environment = settings.ENVIRONMENT
    correlation_id = get_correlation_id()

    # HTTP / Starlette HTTP exceptions: let FastAPI's default logic handle structure
    if isinstance(exc, StarletteHTTPException):
        # Wrap into our structure but preserve status code & detail
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", "An error occurred")
        http_error_body: dict[str, Any] = {
            "correlation_id": correlation_id,
            "type": "http_error",
        }
        if environment != "production":
            http_error_body["details"] = {"detail": detail}
            http_error_body["exception_type"] = exc.__class__.__name__
        return JSONResponse(
            status_code=status_code,
            content=ErrorResponse(
                message="An HTTP error occurred", error=http_error_body, success=False
            ).model_dump(),
        )

    # Pydantic / FastAPI validation errors
    if isinstance(exc, ValidationError | RequestValidationError):
        structured_logger.warning(
            "Validation error",
            validation_errors=getattr(exc, "errors", lambda: [])(),
        )
        validation_details = None
        try:
            validation_details = exc.errors() if hasattr(exc, "errors") else None
        except Exception:  # pragma: no cover - defensive
            validation_details = None

        return _build_error_response(
            correlation_id=correlation_id,
            error_type="validation_error",
            message="Invalid request data provided",
            environment=environment,
            validation_errors=validation_details,
            status_code=422,
        )

    # Integrity / domain
    if isinstance(exc, IntegrityError):
        structured_logger.error("Integrity constraint violation", error=str(exc))
        return _build_error_response(
            correlation_id=correlation_id,
            error_type="integrity_error",
            message=ERROR_TYPE_MESSAGES.get(type(exc), "Integrity error"),
            environment=environment,
        )

    if isinstance(exc, DuplicateUserError | UserNotFoundError):
        structured_logger.warning(
            "Domain error", error_type=exc.__class__.__name__, domain_message=str(exc)
        )
        return _build_error_response(
            correlation_id=correlation_id,
            error_type="domain_error",
            message=ERROR_TYPE_MESSAGES.get(type(exc), "Domain error"),
            environment=environment,
        )

    # Generic fallback
    structured_logger.exception(
        "Unhandled exception", exception_type=exc.__class__.__name__, error=str(exc)
    )
    traceback_str: str | None = None
    if environment != "production":
        import traceback as _tb  # local import to avoid unused in production

        traceback_str = "".join(_tb.format_exception(exc)).strip()

    return _build_error_response(
        correlation_id=correlation_id,
        error_type="internal_server_error",
        message="An internal error occurred",
        environment=environment,
        traceback_str=traceback_str,
        exception_type=exc.__class__.__name__ if environment != "production" else None,
    )


def setup_logging() -> None:
    """Configure application logging with proper JSON structure and idempotent setup."""
    settings = get_settings()

    # Configure root logger
    log_level = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO
    root_logger = logging.getLogger()

    # Make setup idempotent - avoid duplicate handlers
    if root_logger.handlers:
        return

    # Configure format based on environment
    # Pre-declare formatter with the broader logging.Formatter type so mypy
    # can validate assignments from either the third-party JsonFormatter or
    # our fallback implementation.
    formatter: logging.Formatter

    if settings.ENVIRONMENT == "production":
        # Use python-json-logger's JsonFormatter for robust JSON logging.
        try:
            # Import the JsonFormatter implementation directly. Some versions of
            # the python-json-logger package expose the formatter in different
            # modules; use a direct import and silence mypy's attr-defined check
            # since the package provides a typed shim but static analysis can
            # occasionally be stricter than runtime behavior.
            from pythonjsonlogger.jsonlogger import JsonFormatter  # type: ignore

            formatter = JsonFormatter(
                fmt="%(timestamp)s %(level)s %(name)s %(message)s"
            )
        except Exception:
            # Fallback to a simple JSON serializer if the package isn't available
            class JSONFormatter(logging.Formatter):
                def format(self, record: logging.LogRecord) -> str:
                    log_entry = {
                        "timestamp": self.formatTime(record),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                    }
                    if hasattr(record, "structured_data"):
                        log_entry.update(record.structured_data)
                    if record.exc_info:
                        log_entry["exception"] = self.formatException(record.exc_info)
                    return json.dumps(log_entry)

            formatter = JSONFormatter()
    else:
        # Human-readable logging for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Configure handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    # Configure root logger
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers in production
    if settings.ENVIRONMENT == "production":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
