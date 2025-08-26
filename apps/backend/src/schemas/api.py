"""API response schemas.

This module defines the common API response formats used across the application.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, Field


# Type variable for generic response types
T = TypeVar("T")


class ApiResponse[T](BaseModel):
    """Standard API response wrapper.

    This class provides a standardized format for all API responses,
    with consistent fields for success status, data payload, and error messages.

    Attributes:
        success: Whether the request was successful.
        data: The actual response data (when success is True).
        message: A human-readable message about the response.
        error: Error details (when success is False).
    """

    success: bool = True
    data: T | None = None
    message: str = "Operation completed successfully"
    error: dict[str, Any] | None = None


class PaginatedResponse(ApiResponse[T]):
    """Paginated API response.

    Extension of the standard API response that includes pagination metadata.

    Attributes:
        page: Current page number.
        page_size: Number of items per page.
        total: Total number of items across all pages.
        total_pages: Total number of pages.
    """

    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1)
    total: int = 0
    total_pages: int = 0


class ErrorResponse(ApiResponse[None]):
    """Error API response.

    A specialized API response for error conditions with a predefined
    success value of False.

    Attributes:
        success: Always False for error responses.
        message: A human-readable error message.
        error: Additional error details.
    """

    success: bool = False
    message: str = "An error occurred"
    error: dict[str, Any] | None = None
