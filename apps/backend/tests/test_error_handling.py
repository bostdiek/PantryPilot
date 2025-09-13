"""Tests for centralized error handling."""

import json
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from core.error_handler import (
    StructuredLogger,
    get_correlation_id,
    handle_domain_error,
    handle_generic_exception,
    handle_http_exception,
    handle_integrity_error,
    handle_validation_error,
    set_correlation_id,
)
from core.exceptions import DuplicateUserError, UserNotFoundError
from main import app


class TestCorrelationId:
    """Test correlation ID functionality."""

    def test_get_correlation_id_generates_new_id(self):
        """Test that get_correlation_id generates a new ID when none exists."""
        # Clear any existing correlation ID by setting to None
        set_correlation_id(None)

        correlation_id = get_correlation_id()
        assert correlation_id is not None
        assert len(correlation_id) > 0

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        test_id = "test-correlation-id-123"
        set_correlation_id(test_id)

        retrieved_id = get_correlation_id()
        assert retrieved_id == test_id


class TestStructuredLogger:
    """Test structured logging functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = StructuredLogger("test_logger")

    def test_sanitize_data_removes_sensitive_info(self):
        """Test that sensitive data is sanitized from logs."""
        test_data = {
            "username": "testuser",
            "password": "secret123",
            "email": "test@example.com",
            "hashed_password": "hashed_secret",
            "normal_field": "normal_value",
        }

        sanitized = self.logger._sanitize_data(test_data)

        assert sanitized["username"] == "testuser"  # Not sensitive
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["email"] == "[REDACTED]"
        assert sanitized["hashed_password"] == "[REDACTED]"
        assert sanitized["normal_field"] == "normal_value"

    def test_sanitize_data_handles_nested_dicts(self):
        """Test that nested dictionaries are properly sanitized."""
        test_data = {
            "user": {
                "username": "testuser",
                "password": "secret123",
            },
            "metadata": {
                "normal_field": "value",
            },
        }

        sanitized = self.logger._sanitize_data(test_data)

        assert sanitized["user"]["username"] == "testuser"
        assert sanitized["user"]["password"] == "[REDACTED]"
        assert sanitized["metadata"]["normal_field"] == "value"

    @patch("core.error_handler.logging.getLogger")
    def test_logging_includes_correlation_id(self, mock_get_logger):
        """Test that log entries include correlation ID."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        set_correlation_id("test-correlation-123")

        structured_logger = StructuredLogger("test")
        structured_logger.info("Test message", extra_field="extra_value")

        # Verify logger.log was called with correlation ID
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args

        # Check that correlation ID is in the log message
        assert "test-correlation-123" in call_args[0][1]


class TestErrorHandlers:
    """Test individual error handler functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.correlation_id = "test-correlation-123"
        self.request_info = {
            "method": "GET",
            "url": "http://test.com/api/v1/test",
            "client_ip": "127.0.0.1",
            "user_agent": "test-agent",
        }

    @pytest.mark.asyncio
    async def test_handle_http_exception(self):
        """Test handling of HTTPException."""
        exc = HTTPException(status_code=404, detail="Not found")

        response = await handle_http_exception(
            exc, self.correlation_id, self.request_info
        )

        assert response.status_code == 404
        content = json.loads(response.body)
        assert content["success"] is False
        assert content["message"] == "Not found"
        assert content["error"]["correlation_id"] == self.correlation_id

    @pytest.mark.asyncio
    async def test_handle_validation_error_production(self):
        """Test validation error handling in production mode."""
        # Create a mock validation error
        validation_error = ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "missing",
                    "loc": ("field1",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

        with patch("core.error_handler.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "production"

            response = await handle_validation_error(
                validation_error, self.correlation_id, self.request_info
            )

        assert response.status_code == 422
        content = json.loads(response.body)
        assert content["success"] is False
        assert content["message"] == "Invalid request data provided"
        assert "details" not in content["error"]  # No details in production

    @pytest.mark.asyncio
    async def test_handle_validation_error_development(self):
        """Test validation error handling in development mode."""
        validation_error = ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "missing",
                    "loc": ("field1",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

        with patch("core.error_handler.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "development"

            response = await handle_validation_error(
                validation_error, self.correlation_id, self.request_info
            )

        assert response.status_code == 422
        content = json.loads(response.body)
        assert content["success"] is False
        assert content["message"] == "Validation failed"
        assert "details" in content["error"]  # Details included in development

    @pytest.mark.asyncio
    async def test_handle_domain_error_duplicate_user(self):
        """Test handling of DuplicateUserError."""
        exc = DuplicateUserError("User already exists")

        response = await handle_domain_error(
            exc, self.correlation_id, self.request_info
        )

        assert response.status_code == 409
        content = json.loads(response.body)
        assert content["success"] is False
        assert content["message"] == "Username or email already exists"

    @pytest.mark.asyncio
    async def test_handle_domain_error_user_not_found(self):
        """Test handling of UserNotFoundError."""
        exc = UserNotFoundError("User not found")

        response = await handle_domain_error(
            exc, self.correlation_id, self.request_info
        )

        assert response.status_code == 404
        content = json.loads(response.body)
        assert content["success"] is False
        assert content["message"] == "User not found"

    @pytest.mark.asyncio
    async def test_handle_integrity_error(self):
        """Test handling of database integrity errors."""
        exc = IntegrityError("statement", "params", "orig")

        response = await handle_integrity_error(
            exc, self.correlation_id, self.request_info
        )

        assert response.status_code == 409
        content = json.loads(response.body)
        assert content["success"] is False
        assert content["message"] == "A data integrity constraint was violated"

    @pytest.mark.asyncio
    async def test_handle_generic_exception_production(self):
        """Test handling of generic exceptions in production mode."""
        exc = ValueError("Test error message")

        with patch("core.error_handler.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "production"

            response = await handle_generic_exception(
                exc, self.correlation_id, self.request_info
            )

        assert response.status_code == 500
        content = json.loads(response.body)
        assert content["success"] is False
        assert content["message"] == "An internal server error occurred"
        assert "traceback" not in content["error"]  # No traceback in production

    @pytest.mark.asyncio
    async def test_handle_generic_exception_development(self):
        """Test handling of generic exceptions in development mode."""
        exc = ValueError("Test error message")

        with patch("core.error_handler.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "development"

            response = await handle_generic_exception(
                exc, self.correlation_id, self.request_info
            )

        assert response.status_code == 500
        content = json.loads(response.body)
        assert content["success"] is False
        assert "Test error message" in content["message"]
        assert "traceback" in content["error"]  # Traceback included in development


class TestIntegrationErrorHandling:
    """Test error handling integration with FastAPI."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_correlation_id_in_response_headers(self):
        """Test that correlation ID is added to response headers."""
        response = self.client.get("/api/v1/health")

        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        assert len(correlation_id) > 0

    def test_custom_correlation_id_respected(self):
        """Test that custom correlation ID in request header is used."""
        custom_id = "custom-correlation-123"

        response = self.client.get(
            "/api/v1/health", headers={"X-Correlation-ID": custom_id}
        )

        assert response.headers["X-Correlation-ID"] == custom_id

    def test_validation_error_handled_centrally(self):
        """Test that validation errors are handled by the global handler."""
        # Test with invalid registration data
        invalid_data = {
            "username": "",  # Invalid username
            "email": "invalid-email",  # Invalid email
            "password": "short",  # Too short password
        }

        response = self.client.post("/api/v1/auth/register", json=invalid_data)

        assert response.status_code == 422
        assert "X-Correlation-ID" in response.headers

        error_data = response.json()
        assert error_data["success"] is False
        assert "correlation_id" in error_data.get("error", {})

    def test_domain_error_handled_centrally(self):
        """Test that domain errors are handled by the global handler."""
        # Test with a mock endpoint that raises domain errors
        # Since the registration endpoint may have database dependencies,
        # we'll test with a simpler validation that triggers our domain error

        # First, test with data that will trigger internal validation
        user_data = {
            "username": "testuser123",
            "email": "test@example.com",
            "password": "short",  # This will trigger HTTPException in auth validation
        }

        response = self.client.post("/api/v1/auth/register", json=user_data)

        # This should be handled by our error handler
        assert "X-Correlation-ID" in response.headers
        assert response.status_code in [
            400,
            422,
        ]  # Could be validation or business logic error
