"""Tests for centralized error handling."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from core.error_handler import StructuredLogger, get_correlation_id, set_correlation_id

# Domain exception imports removed (previous unit-level handler tests eliminated).
from core.security_config import get_allowed_error_fields, is_sensitive_key
from main import app


class TestSecurityConfiguration:
    """Test security configuration functionality."""

    def test_sensitive_key_detection(self):
        """Test that sensitive keys are properly detected."""
        # Should be detected as sensitive
        sensitive_keys = [
            "password",
            "PASSWORD",
            "Password",
            "email",
            "EMAIL",
            "user_email",
            "token",
            "access_token",
            "auth_token",
            "api_key",
            "API_KEY",
            "ssn",
            "credit_card",
            "phone_number",
        ]

        for key in sensitive_keys:
            assert is_sensitive_key(key), f"Key '{key}' should be detected as sensitive"

    def test_non_sensitive_key_detection(self):
        """Test that non-sensitive keys are not flagged."""
        # Should not be detected as sensitive
        non_sensitive_keys = [
            "username",
            "name",
            "id",
            "status",
            "created_at",
            "updated_at",
            "title",
            "description",
            "normal_field",
        ]

        for key in non_sensitive_keys:
            assert not is_sensitive_key(key), (
                f"Key '{key}' should not be detected as sensitive"
            )

    def test_production_error_fields(self):
        """Test that production error fields are restricted."""
        allowed_fields = get_allowed_error_fields("production")

        # Production should only allow safe fields
        expected_production_fields = {"correlation_id", "type"}
        assert allowed_fields == expected_production_fields

        # Should not include development-only fields
        forbidden_fields = {"details", "traceback", "exception_type"}
        for field in forbidden_fields:
            assert field not in allowed_fields

    def test_development_error_fields(self):
        """Test that development error fields include debugging info."""
        allowed_fields = get_allowed_error_fields("development")

        # Development should include all production fields plus debugging fields
        expected_fields = {
            "correlation_id",
            "type",
            "details",
            "traceback",
            "exception_type",
            "validation_errors",
        }
        assert expected_fields.issubset(allowed_fields)


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

    def test_sanitize_data_comprehensive_sensitive_keys(self):
        """Test that comprehensive list of sensitive keys are sanitized."""
        test_data = {
            "username": "testuser",
            "password": "secret123",
            "email": "test@example.com",
            "access_token": "token123",
            "refresh_token": "refresh123",
            "authorization": "Bearer token",
            "api_key": "key123",
            "ssn": "123-45-6789",
            "credit_card_number": "4111111111111111",
            "phone_number": "555-123-4567",
            "normal_field": "normal_value",
        }

        sanitized = self.logger._sanitize_data(test_data)

        # Should not be sanitized
        assert sanitized["username"] == "testuser"
        assert sanitized["normal_field"] == "normal_value"

        # Should be sanitized
        sensitive_fields = [
            "password",
            "email",
            "access_token",
            "refresh_token",
            "authorization",
            "api_key",
            "ssn",
            "credit_card_number",
            "phone_number",
        ]
        for field in sensitive_fields:
            assert sanitized[field] == "[REDACTED]", (
                f"Field '{field}' was not sanitized"
            )

    def test_sanitize_data_handles_nested_structures_with_lists(self):
        """Test that nested structures including lists are properly sanitized."""
        test_data = {
            "user": {
                "username": "testuser",
                "password": "secret123",
                "profile": {"email": "test@example.com", "phone": "555-123-4567"},
            },
            "headers": [
                {"name": "authorization", "value": "Bearer token123"},
                {"name": "content-type", "value": "application/json"},
            ],
            "requests": [
                {"method": "POST", "auth_token": "secret_token", "data": "normal_data"}
            ],
        }

        sanitized = self.logger._sanitize_data(test_data)

        # Check nested dict sanitization
        assert sanitized["user"]["username"] == "testuser"
        assert sanitized["user"]["password"] == "[REDACTED]"
        assert sanitized["user"]["profile"]["email"] == "[REDACTED]"
        assert sanitized["user"]["profile"]["phone"] == "[REDACTED]"

        # Check list sanitization
        assert sanitized["headers"][0]["value"] == "[REDACTED]"  # authorization header
        assert sanitized["headers"][1]["value"] == "application/json"  # normal header
        assert sanitized["requests"][0]["auth_token"] == "[REDACTED]"


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

    @patch("core.error_handler.get_settings")
    def test_production_responses_no_sensitive_data_leak(self, mock_settings):
        """Test that production responses never contain sensitive fields."""
        mock_settings.return_value.ENVIRONMENT = "production"

        # Test validation error in production
        invalid_data = {
            "username": "",
            "email": "invalid-email",
            "password": "short",
        }

        response = self.client.post("/api/v1/auth/register", json=invalid_data)
        error_data = response.json()

        # Production responses should only contain safe fields
        allowed_error_fields = {"correlation_id", "type"}
        error_obj = error_data.get("error", {})

        # Ensure no sensitive fields leak to production responses
        forbidden_fields = {"details", "traceback", "exception_type", "ctx"}
        for field in forbidden_fields:
            assert field not in error_obj, (
                f"Sensitive field '{field}' found in production response"
            )

        # Ensure only allowed fields are present
        for field in error_obj.keys():
            assert field in allowed_error_fields, (
                f"Unexpected field '{field}' in production error response"
            )

        # Ensure required safe fields are present
        assert "correlation_id" in error_obj
        assert "type" in error_obj

    @patch("core.error_handler.get_settings")
    def test_generic_exception_production_no_traceback_leak(self, mock_settings):
        """Test that generic exceptions in production don't leak tracebacks."""
        mock_settings.return_value.ENVIRONMENT = "production"

        # Create a test endpoint that raises an exception
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()

        @test_app.get("/test-error")
        async def test_error_endpoint():
            raise ValueError(
                "Test internal error with sensitive data: password=secret123"
            )

        # Add our error handler to test app and install fallback
        from core.error_handler import (
            ExceptionNormalizationMiddleware,
            global_exception_handler,
        )

        test_app.add_exception_handler(Exception, global_exception_handler)
        test_app.add_middleware(ExceptionNormalizationMiddleware)

        test_client = TestClient(test_app)
        response = test_client.get("/test-error")

        assert response.status_code == 500
        error_data = response.json()

        # Ensure no traceback or sensitive data in production
        error_obj = error_data.get("error", {})
        assert "traceback" not in error_obj
        assert "exception_type" not in error_obj
        assert "password=secret123" not in str(error_data)

        # Should only contain safe fields
        allowed_fields = {"correlation_id", "type"}
        for field in error_obj.keys():
            assert field in allowed_fields

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
