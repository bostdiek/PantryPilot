from src.core.error_handler import StructuredLogger


def test_structured_logger_redacts_sensitive_keys(monkeypatch):
    logger = StructuredLogger("tests")

    # Provide a deterministic correlation id
    monkeypatch.setenv("ENVIRONMENT", "development")

    # use non-sensitive placeholder values to avoid secret-detection false positives
    # allowlist: this is a test fixture value and not a real secret
    data = {
        "password": "placeholder_password",  # pragma: allowlist secret
        "email": "me@example.com",
        "name": "alice",
    }
    sanitized = logger._sanitize_data(data)

    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["email"] == "[REDACTED]"
    assert sanitized["name"] == "alice"


def test_structured_logger_header_like_redaction(monkeypatch):
    logger = StructuredLogger("tests")
    monkeypatch.setenv("ENVIRONMENT", "development")

    # header value uses a benign placeholder token
    header = {"name": "Authorization", "value": "Bearer placeholder_token"}
    redacted = logger._redact_header_like(header)
    # header-like should be redacted
    assert redacted["value"] == "[REDACTED]"
