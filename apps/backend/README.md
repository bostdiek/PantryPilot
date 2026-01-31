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

## LLM Configuration

PantryPilot supports two LLM providers for all AI features:

### Azure OpenAI (Recommended for Production)

Azure OpenAI provides enterprise-grade reliability and data privacy for production deployments.

```bash
# Enable Azure OpenAI for all AI features
LLM_PROVIDER=azure_openai

# Azure OpenAI resource endpoint
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# API key from Azure Portal or Key Vault
AZURE_OPENAI_API_KEY=your-api-key

# Model deployments (must match Azure deployment names)
CHAT_MODEL=gpt-4o-mini                    # Chat, recipe extraction, titles
MULTIMODAL_MODEL=gpt-4o                   # Image-based recipe extraction
TEXT_MODEL=gpt-4o-mini                    # Text-only generation
EMBEDDING_MODEL=text-embedding-3-small    # Semantic search

# API version (optional, defaults to 2024-10-01-preview)
AZURE_OPENAI_API_VERSION=2024-10-01-preview
```

**Required Azure OpenAI Deployments:**
- `gpt-4o-mini` or similar: Chat agent, URL recipe extraction, title generation
- `gpt-4o` or multimodal model: Image-based recipe extraction
- `text-embedding-3-small`: Semantic search embeddings (configured for 768 dimensions)

**Setup via Bicep:**
The project includes Bicep infrastructure for Azure OpenAI. Set `deployAzureOpenAI=true` in your parameters file to provision all required model deployments automatically.

### Google Gemini (Development Default)

Gemini is the default provider for local development due to simpler setup.

```bash
# Use Gemini (default when LLM_PROVIDER is unset or =gemini)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key

# Model names (optional, defaults to Gemini models)
CHAT_MODEL=gemini-2.5-flash
MULTIMODAL_MODEL=gemini-2.5-flash-lite
TEXT_MODEL=gemini-2.5-flash-lite
EMBEDDING_MODEL=gemini-embedding-001
```

### AI Features Coverage

When `LLM_PROVIDER=azure_openai`, the following features use Azure OpenAI:

| Feature | Configuration Variable | Default (Gemini) |
|---------|----------------------|------------------|
| Chat Agent | `CHAT_MODEL` | gemini-2.5-flash |
| Recipe Extraction (URL) | `CHAT_MODEL` | gemini-2.5-flash |
| Recipe Extraction (Image) | `MULTIMODAL_MODEL` | gemini-2.5-flash-lite |
| Title Generation | `TEXT_MODEL` | gemini-2.5-flash-lite |
| Context Generation | `TEXT_MODEL` | gemini-2.5-flash-lite |
| Semantic Search | `EMBEDDING_MODEL` | gemini-embedding-001 |

All providers support tool calling and structured outputs.

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

### Prompt and Tool Iteration Workflow

The PydanticAI Web UI provides a low-friction workflow for iterating on:

1. **System Prompts**: Edit `CHAT_SYSTEM_PROMPT` in `services/chat_agent.py` and restart the UI
2. **Tool Behavior**: Modify tool implementations in `services/weather.py` or `services/web_search.py`
3. **Output Schema**: Adjust `AssistantMessage` in `schemas/chat_content.py` for response structure

**Workflow:**
```bash
# 1. Make changes to prompts/tools
# 2. Restart the dev UI (Ctrl+C and re-run)
PYTHONPATH=./src uv run --env-file ../../.env.dev python -m dev.pydanticai_ui

# 3. Test in browser at http://127.0.0.1:8021
# 4. Iterate until behavior is correct
# 5. Run tests to verify no regressions
uv run pytest tests/ -k chat -v
```

**Note:** The dev UI does NOT require the full Docker stack. It connects directly to a local PostgreSQL database (ensure `POSTGRES_*` env vars are set).

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

## Observability (Production)

The backend supports Azure Monitor Application Insights via OpenTelemetry for production observability.

### Configuration

```bash
# Enable observability in production
ENABLE_OBSERVABILITY=true
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...;IngestionEndpoint=...

# Custom service name (optional)
OTEL_SERVICE_NAME=pantrypilot-backend
```

### What Gets Traced

- HTTP requests (FastAPI auto-instrumentation)
- Database queries (SQLAlchemy auto-instrumentation)
- External API calls (httpx auto-instrumentation)
- Custom chat/tool execution spans

### PII Safety

**NEVER** log or add to spans:
- User message content
- Recipe content or personal preferences
- API keys, tokens, or credentials
- Location data beyond city-level

See `core/observability.py` and `docs/SECURITY_IMPLEMENTATION.md` for full guidance.

---
For questions or improvements, open an issue or submit a PR with a proposed change plus tests.
