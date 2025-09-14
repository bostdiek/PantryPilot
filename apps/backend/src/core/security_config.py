"""Security configuration constants for PantryPilot API.

This module centralizes security-related configuration including:
- Sensitive keys that should be sanitized from logs
- Error handling security settings
- Other security-related constants
"""

# No external typing imports needed; use built-in generics (PEP 585)

# Comprehensive list of sensitive keys for sanitization
# These keys will be automatically redacted from logs to prevent PII leakage
SENSITIVE_KEYS: set[str] = {
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
    "bearer",
    # Personal Identifiable Information
    "email",
    "phone",
    "phone_number",
    "ssn",
    "social_security_number",
    "address",
    "street_address",
    "home_address",
    "billing_address",
    "shipping_address",
    "credit_card",
    "credit_card_number",
    "card_number",
    "cvv",
    "card_cvv",
    "bank_account",
    "routing_number",
    "account_number",
    # Additional sensitive headers and fields
    "set-cookie",
    "cookie",
    "x-auth-token",
    "x-api-key",
    "x-session-id",
    "x-csrf-token",
    "authentication",
    "auth",
    "login",
}

# Production-only error response fields
# In production, error responses should only contain these fields to
# prevent information leakage
PRODUCTION_ERROR_FIELDS: set[str] = {
    "correlation_id",
    "type",
}

# Development error response fields (additional fields allowed in development)
DEVELOPMENT_ERROR_FIELDS: set[str] = PRODUCTION_ERROR_FIELDS | {
    "details",
    "traceback",
    "exception_type",
    "validation_errors",
}


def get_allowed_error_fields(environment: str) -> set[str]:
    """Get allowed error response fields based on environment.

    Args:
        environment: The application environment (production, development, etc.)

    Returns:
        Set of allowed field names for error responses
    """
    if environment == "production":
        return PRODUCTION_ERROR_FIELDS.copy()
    else:
        return DEVELOPMENT_ERROR_FIELDS.copy()


def is_sensitive_key(key: str) -> bool:
    """Check if a key should be considered sensitive and redacted.

    Args:
        key: The key name to check

    Returns:
        True if the key should be redacted, False otherwise
    """
    key_lower = key.lower()
    return any(sensitive in key_lower for sensitive in SENSITIVE_KEYS)
