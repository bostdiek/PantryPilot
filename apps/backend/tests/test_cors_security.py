"""Tests for CORS configuration and security headers."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestCORSConfiguration:
    """Test CORS configuration adheres to security requirements."""

    def test_cors_preflight_request(self, client):
        """Test CORS preflight request is handled correctly."""
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
        assert "Access-Control-Allow-Credentials" in response.headers
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

    def test_cors_simple_request_allowed_origin(self, client):
        """Test CORS for simple request from allowed origin."""
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:5173"},
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
        assert "Access-Control-Allow-Credentials" in response.headers
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

    def test_cors_request_from_disallowed_origin(self, client):
        """Test CORS blocks requests from disallowed origins."""
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://malicious-site.com"},
        )
        
        # Should still respond but without CORS headers for disallowed origin
        assert response.status_code == 200
        # The origin should not be in the Access-Control-Allow-Origin header
        # or the header should be absent
        if "Access-Control-Allow-Origin" in response.headers:
            assert response.headers["Access-Control-Allow-Origin"] != "http://malicious-site.com"

    def test_cors_multiple_allowed_origins(self, client):
        """Test that multiple configured origins are handled correctly."""
        # Test first allowed origin
        response1 = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response1.status_code == 200
        assert response1.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
        
        # Test second allowed origin (if configured)
        response2 = client.get(
            "/api/v1/health", 
            headers={"Origin": "http://127.0.0.1:5173"},
        )
        assert response2.status_code == 200
        # Note: FastAPI CORS middleware returns the requesting origin if it's allowed,
        # not all allowed origins


class TestSecurityHeaders:
    """Test that security headers are properly configured."""

    def test_security_headers_not_set_by_backend(self, client):
        """Test that security headers are not set by backend (nginx handles them)."""
        response = client.get("/api/v1/health")
        
        # These headers should be set by nginx, not FastAPI
        security_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy"
        ]
        
        for header in security_headers:
            # Backend should not set these headers - nginx will add them
            assert header not in response.headers, f"Backend should not set {header}"

    def test_api_response_headers(self, client):
        """Test API-specific response headers."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        # FastAPI should set content-type
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]


class TestCORSConfigValidation:
    """Test CORS configuration validation logic."""

    def test_cors_credentials_with_wildcard_prevented(self):
        """Test that wildcard origins are prevented when credentials are allowed."""
        from core.config import Settings
        
        # This should raise a validation error
        with pytest.raises(ValueError, match="CORS configuration error"):
            Settings(
                SECRET_KEY="test-key",
                CORS_ORIGINS=["*"],
                ALLOW_CREDENTIALS=True,
            )

    def test_cors_credentials_without_wildcard_allowed(self):
        """Test that specific origins are allowed when credentials are enabled."""
        from core.config import Settings
        
        # This should not raise an error
        settings = Settings(
            SECRET_KEY="test-key",
            CORS_ORIGINS=["http://localhost:5173", "https://app.example.com"],
            ALLOW_CREDENTIALS=True,
        )
        
        assert settings.ALLOW_CREDENTIALS is True
        assert "*" not in settings.CORS_ORIGINS

    def test_cors_origins_csv_parsing(self):
        """Test that CORS origins can be parsed from CSV string."""
        from core.config import Settings
        
        settings = Settings(
            SECRET_KEY="test-key",
            CORS_ORIGINS="http://localhost:5173,https://app.example.com, http://127.0.0.1:5173",
            ALLOW_CREDENTIALS=True,
        )
        
        expected_origins = [
            "http://localhost:5173",
            "https://app.example.com", 
            "http://127.0.0.1:5173"
        ]
        
        assert settings.CORS_ORIGINS == expected_origins

    def test_cors_origins_json_parsing(self):
        """Test that CORS origins can be parsed from JSON string."""
        from core.config import Settings
        
        settings = Settings(
            SECRET_KEY="test-key",
            CORS_ORIGINS='["http://localhost:5173", "https://app.example.com"]',
            ALLOW_CREDENTIALS=True,
        )
        
        expected_origins = ["http://localhost:5173", "https://app.example.com"]
        assert settings.CORS_ORIGINS == expected_origins