# PantryPilot Backend

## Centralized Error Handling

The backend uses a centralized error handling strategy implemented in `core.error_handler` to ensure:

* Consistent JSON error envelope
* Inclusion of a correlation ID for every error (`X-Correlation-ID` header)
* Redaction of sensitive fields in logs and responses (production safe subset)
* Environment-aware verbosity (development includes diagnostics; production stays minimal)

### Response Envelope

All error responses conform to the `ErrorResponse` schema:

```json
{
  "success": false,
  "message": "High-level message",
  "error": {
    "correlation_id": "<uuid>",
    "type": "<error_type>",
    "details": { "optional": true },
    "exception_type": "ValueError",
    "traceback": "<stack>",
    "validation_errors": [ { "loc": ["field"], "msg": "...", "type": "..." } ]
  }
}
```

### Error Types

| Type | Scenario |
|------|----------|
| `validation_error` | Request body/query/path validation failures (422) |
| `http_error` | Explicit HTTP-esque errors surfaced via Starlette/FastAPI exceptions (status varies) |
| `domain_error` | Domain-specific exceptions (e.g. user not found, duplicate) |
| `integrity_error` | Database constraint violations |
| `internal_server_error` | Any other uncaught exception |

### Production vs Development Field Matrix

| Field | Production | Development |
|-------|------------|-------------|
| `correlation_id` | Yes | Yes |
| `type` | Yes | Yes |
| `details` | No | Yes |
| `exception_type` | No | Yes |
| `traceback` | No | Yes |
| `validation_errors` | No (even for 422) | Yes (for validation errors) |

### Correlation IDs

`CorrelationIdMiddleware` ensures each request has a stable correlation ID propagated to:

* Response header: `X-Correlation-ID`
* Log records (structured data)
* Error payloads (`error.correlation_id`)

Custom clients can provide `X-Correlation-ID`; otherwise a UUID is generated.

### Logging

`StructuredLogger` emits:

* JSON logs in production (one object per line) with merged structured payload
* Readable text in development
* Automatic redaction of keys matching the security-configured sensitive set

### Adding New Domain Errors

1. Define a subclass of `DomainError` in `core/exceptions.py`.
2. (Optional) Add a human-friendly default in `ERROR_TYPE_MESSAGES` mapping.
3. Raise it inside business logic – the global handler will classify it as `domain_error`.

### Extending Behavior

If you need a new error classification:

1. Add the exception class.
2. Add an `elif isinstance(exc, NewType):` block in `global_exception_handler` before the generic fallback.
3. Return via `_build_error_response()` with the new `error_type`.

### Sample Production Validation Error (HTTP 422)

```json
{
  "success": false,
  "message": "Invalid request data provided",
  "error": {
    "correlation_id": "0d8d7b5e-4d4c-4ac4-8ed2-9f6f6a099a0d",
    "type": "validation_error"
  }
}
```

### Sample Development Generic Error (HTTP 500)

```json
{
  "success": false,
  "message": "An internal error occurred",
  "error": {
    "correlation_id": "aa5c2dbe-8c99-4d9d-9f8b-0b2b6e18f2f1",
    "type": "internal_server_error",
    "exception_type": "RuntimeError",
    "traceback": "RuntimeError: Something broke...",
    "details": {"detail": "Optional diagnostic context"}
  }
}
```

### Testing Strategy

* Integration coverage in `tests/test_error_handling.py` for high-level flows.
* Focused unit coverage in `tests/test_error_handler_unit.py` for environment differences.

### Middleware Stack

Registered in `main.py` (order matters):

1. `CorrelationIdMiddleware`
2. `ExceptionNormalizationMiddleware` (final safety net)

### Gotchas

* Always register `global_exception_handler` for `Exception` and `RequestValidationError` to catch early.
* Avoid re-raising inside the handler unless intentionally delegating.
* Never log raw request bodies containing secrets; rely on structured logger sanitization.

---

## Agent Playground (Dev Only)

Use the PydanticAI Web UI to iterate on the chat assistant locally:

1. `cd apps/backend`
2. Ensure required model env vars are set (e.g. `GEMINI_API_KEY`).
3. `PYTHONPATH=./src uv run --env-file ../../.env.dev python -m dev.pydanticai_ui`

The UI starts on http://127.0.0.1:8021 and uses the shared chat agent tools.

### Dev User Context

The UI automatically creates or uses a `dev` user with the following context:

- **Location**: Boston, MA (42.3601, -71.0589) for weather tool testing
- **Timezone**: America/New_York

### Testing Tools via API

To test the chat tools via the REST API instead:

```bash
# 1. Login as dev user
#    By default in local dev, the `dev` user is created with password `dev_password_123`
#    (see dev/pydanticai_ui.py). If you override this in .env.dev or a seed script,
#    update the password value below accordingly.
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=dev&password=dev_password_123"

# 2. Use the returned token to call the chat streaming endpoint
curl -X POST "http://localhost:8000/api/v1/chat/conversations/{uuid}/messages/stream" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "What is the weather like today?"}'
```

The chat agent has access to these internal tools:
- `get_daily_weather`: Returns 7-day forecast based on user's location preferences
- `web_search`: Searches the web using Brave Search API for recipes and information

---
For questions or improvements, open an issue or submit a PR with a proposed change plus tests.
