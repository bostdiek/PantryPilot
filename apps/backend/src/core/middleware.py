"""Middleware for request correlation ID tracking."""

import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.error_handler import set_correlation_id


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and track correlation IDs for requests.
    
    This middleware:
    - Generates unique correlation IDs for each request
    - Sets the correlation ID in the request context
    - Adds correlation ID to response headers
    - Enables request tracing across the application
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID."""
        # Check if correlation ID is provided in request headers
        correlation_id = request.headers.get("X-Correlation-ID")
        
        # Generate new correlation ID if not provided
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Set correlation ID in context for the request
        set_correlation_id(correlation_id)
        
        # Add correlation ID to request state for access in endpoints
        request.state.correlation_id = correlation_id
        
        # Process the request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response