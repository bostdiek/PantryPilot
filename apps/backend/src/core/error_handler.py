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
import traceback
import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.config import get_settings
from core.exceptions import DomainError, DuplicateUserError, UserNotFoundError
from core.security_config import get_allowed_error_fields, is_sensitive_key
from schemas.api import ErrorResponse


# Comprehensive list of sensitive keys for sanitization
SENSITIVE_KEYS = {
    # Authentication & Authorization
    "password",
    "hashed_password", 
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "auth_token",
    "api_key",
    "key",
    "jwt",
    "session_id",
    "csrf_token",
    "otp",
    "pin",
    "security_code",
    
    # Personal Identifiable Information
    "email",
    "phone",
    "phone_number",
    "ssn",
    "social_security_number",
    "address",
    "street_address",
    "credit_card",
    "credit_card_number",
    "card_number",
    "cvv",
    "card_cvv",
    "bank_account",
    "routing_number",
    
    # Additional sensitive headers and fields
    "set-cookie",
    "cookie",
    "x-auth-token",
    "x-api-key",
}

# Comprehensive list of sensitive keys for sanitization
SENSITIVE_KEYS = {
    # Authentication & Authorization
    "password",
    "hashed_password", 
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "auth_token",
    "api_key",
    "key",
    "jwt",
    "session_id",
    "csrf_token",
    "otp",
    "pin",
    "security_code",
    
    # Personal Identifiable Information
    "email",
    "phone",
    "phone_number",
    "ssn",
    "social_security_number",
    "address",
    "street_address",
    "credit_card",
    "credit_card_number",
    "card_number",
    "cvv",
    "card_cvv",
    "bank_account",
    "routing_number",
    
    # Additional sensitive headers and fields
    "set-cookie",
    "cookie",
    "x-auth-token",
    "x-api-key",
}

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
            # In production, log the full structured data as valid JSON
            try:
                structured_message = json.dumps(log_data)
                self.logger.log(level, structured_message, exc_info=exc_info)
            except (TypeError, ValueError) as e:
                # Fallback if JSON serialization fails
                fallback_message = f"[{correlation_id}] {message} (JSON serialization failed: {e})"
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

        for key, value in data.items():
            if is_sensitive_key(key):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

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


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for all unhandled exceptions.

    This handler:
    - Logs detailed error information with correlation IDs
    - Returns generic error messages in production
    - Includes debug info in development
    - Prevents sensitive data leakage
    """
    correlation_id = get_correlation_id()

    # Extract request info for logging (sanitized)
    request_info = {
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
    }

    # Handle specific exception types
    if isinstance(exc, HTTPException):
        return await handle_http_exception(exc, correlation_id, request_info)
    elif isinstance(exc, StarletteHTTPException):
        return await handle_starlette_http_exception(exc, correlation_id, request_info)
    elif isinstance(exc, ValidationError | RequestValidationError):
        return await handle_validation_error(exc, correlation_id, request_info)
    elif isinstance(exc, DomainError):
        return await handle_domain_error(exc, correlation_id, request_info)
    elif isinstance(exc, IntegrityError):
        return await handle_integrity_error(exc, correlation_id, request_info)
    else:
        return await handle_generic_exception(exc, correlation_id, request_info)


async def handle_http_exception(
    exc: HTTPException, correlation_id: str, request_info: dict[str, Any]
) -> JSONResponse:
    """Handle FastAPI HTTPException."""
    structured_logger.warning(
        f"HTTP exception: {exc.detail}",
        status_code=exc.status_code,
        **request_info,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            message=exc.detail,
            error={"correlation_id": correlation_id, "type": "http_error"},
        ).model_dump(),
    )


async def handle_starlette_http_exception(
    exc: StarletteHTTPException, correlation_id: str, request_info: dict[str, Any]
) -> JSONResponse:
    """Handle Starlette HTTPException."""
    structured_logger.warning(
        f"Starlette HTTP exception: {exc.detail}",
        status_code=exc.status_code,
        **request_info,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            message=str(exc.detail),
            error={"correlation_id": correlation_id, "type": "http_error"},
        ).model_dump(),
    )


async def handle_validation_error(
    exc: ValidationError | RequestValidationError,
    correlation_id: str,
    request_info: dict[str, Any],
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    settings = get_settings()

    structured_logger.warning(
        "Validation error in request",
        error_count=getattr(exc, "error_count", lambda: len(exc.errors()))(),
        **request_info,
    )

    # Prepare error details dict with environment-aware field filtering
    allowed_fields = get_allowed_error_fields(settings.ENVIRONMENT)
    error_details: dict[str, Any] = {"correlation_id": correlation_id, "type": "validation_error"}

    if settings.ENVIRONMENT == "production":
        # Production: generic message, no details
        message = "Invalid request data provided"
        # Only include allowed production fields
        error_details = {k: v for k, v in error_details.items() if k in allowed_fields}
    else:
        # Development: include validation details for debugging
        message = "Validation failed"
        error_details["details"] = exc.errors()
        # Filter to allowed development fields
        error_details = {k: v for k, v in error_details.items() if k in allowed_fields}

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            message=message,
            error=error_details,
        ).model_dump(),
    )


async def handle_domain_error(
    exc: DomainError, correlation_id: str, request_info: dict[str, Any]
) -> JSONResponse:
    """Handle domain-specific business logic errors."""
    structured_logger.info(
        f"Domain error: {exc.__class__.__name__}",
        error_type=exc.__class__.__name__,
        **request_info,
    )

    # Map domain errors to appropriate HTTP status and messages
    if isinstance(exc, DuplicateUserError):
        status_code = status.HTTP_409_CONFLICT
        message = "Username or email already exists"
    elif isinstance(exc, UserNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        message = "User not found"
    else:
        # Generic domain error
        status_code = status.HTTP_400_BAD_REQUEST
        message = ERROR_TYPE_MESSAGES.get(type(exc), "A business logic error occurred")

    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            success=False,
            message=message,
            error={"correlation_id": correlation_id, "type": "domain_error"},
        ).model_dump(),
    )


async def handle_integrity_error(
    exc: IntegrityError, correlation_id: str, request_info: dict[str, Any]
) -> JSONResponse:
    """Handle database integrity constraint violations."""
    structured_logger.error(
        "Database integrity error",
        error_class=exc.__class__.__name__,
        **request_info,
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=ErrorResponse(
            success=False,
            message="A data integrity constraint was violated",
            error={"correlation_id": correlation_id, "type": "integrity_error"},
        ).model_dump(),
    )


async def handle_generic_exception(
    exc: Exception, correlation_id: str, request_info: dict[str, Any]
) -> JSONResponse:
    """Handle all other unhandled exceptions."""
    settings = get_settings()

    # Log the full exception details for debugging
    structured_logger.exception(
        f"Unhandled exception: {exc.__class__.__name__}",
        error_class=exc.__class__.__name__,
        **request_info,
    )

    # Prepare error details dict with environment-aware field filtering
    allowed_fields = get_allowed_error_fields(settings.ENVIRONMENT)
    error_details: dict[str, Any] = {"correlation_id": correlation_id, "type": "internal_error"}

    if settings.ENVIRONMENT == "production":
        # Production: generic message without details
        message = "An internal server error occurred"
        # Only include allowed production fields
        error_details = {k: v for k, v in error_details.items() if k in allowed_fields}
    else:
        # Development: include exception details for debugging
        message = f"Internal server error: {str(exc)}"
        error_details.update({
            "exception_type": exc.__class__.__name__,
            "traceback": traceback.format_exc().splitlines(),
        })
        # Filter to allowed development fields
        error_details = {k: v for k, v in error_details.items() if k in allowed_fields}

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            message=message,
            error=error_details,
        ).model_dump(),
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
    if settings.ENVIRONMENT == "production":
        # Use proper JSON formatter for production
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                
                # Include structured data if available
                if hasattr(record, 'structured_data'):
                    log_entry.update(record.structured_data)
                
                # Include exception info if present
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
