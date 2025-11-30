# API Design

Base prefix: `/api/v1`
Versioning: Path-based (`/api/v{n}`) with option to add header versioning later.
Response envelope: `ApiResponse<T>` with `success`, `data`, `message`, `error`.

## Endpoints (v1)

- GET `/api/v1/health` — health check
- Authentication
  - POST `/api/v1/auth/login` — user login (OAuth2-compatible)
  - POST `/api/v1/auth/register` — user registration
- Recipes
  - GET `/api/v1/recipes` — list with filters & pagination
  - POST `/api/v1/recipes` — create
  - GET `/api/v1/recipes/{id}` — get by id
  - PUT `/api/v1/recipes/{id}` — update
  - DELETE `/api/v1/recipes/{id}` — delete
- Meal Plans (initial)
  - GET `/api/v1/mealplans/weekly`
  - PUT `/api/v1/mealplans/weekly`
  - POST `/api/v1/meals` `/api/v1/meals/{id}` (see schema)

## Authentication Endpoints

### POST `/api/v1/auth/register`

**Description**: User registration endpoint that creates a new user account

**Request Body**: JSON with UserRegister schema fields
```json
{
  "username": "string (3-32 chars, alphanumeric, underscore, hyphen)",
  "email": "string (valid email address)",
  "password": "string (minimum 12 characters)",
  "first_name": "string (optional)",
  "last_name": "string (optional)"
}
```

**Response**: 201 Created
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

**Error Responses**:
- `400 Bad Request`: Password too short (less than 12 characters)
- `409 Conflict`: Username or email already exists
- `422 Unprocessable Entity`: Validation errors (invalid email, username pattern, missing required fields)

### POST `/api/v1/auth/login`

**Description**: OAuth2-compatible token login, get an access token for future requests

**Request Body**: Form data (OAuth2PasswordRequestForm)
- `username`: The user's username
- `password`: The user's password

**Response**: 200 OK
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

**Error Responses**:
- `401 Unauthorized`: Incorrect username or password

## Schemas

- See `apps/backend/src/schemas/*` for Pydantic models with strict validation.
- Shared enums: `RecipeDifficulty`, `RecipeCategory`.

## Pagination

- Offset/limit parameters; response returns `{ items, limit, offset, total }`.

## Errors

- Standardized error shape via `ApiResponse` with `success=false` and `error` object.
- Canonical error types for consistent client-side handling:

### Authentication Error Types

| Error Type | HTTP Status | Description | Example |
|------------|-------------|-------------|---------|
| `unauthorized` | 401 | Invalid or expired credentials | Token validation failed |
| `forbidden` | 403 | Valid credentials but insufficient permissions | Access to resource denied |

### Other Error Types

| Error Type | HTTP Status | Description |
|------------|-------------|-------------|
| `validation_error` | 422 | Request data validation failed |
| `domain_error` | 500 | Business logic constraint violated |
| `internal_server_error` | 500 | Unexpected server error |
| `http_error` | Various | Generic HTTP error fallback |

### Error Response Format

```json
{
  "success": false,
  "message": "An HTTP error occurred",
  "error": {
    "type": "unauthorized",
    "correlation_id": "uuid-1234-5678",
    "details": {
      "detail": "Could not validate credentials"
    }
  }
}
```

**Note**: The `details` field is only included in non-production environments.

## Rate Limiting

The API implements rate limiting to protect against abuse and ensure fair usage.

### Configuration

Rate limiting is implemented using Upstash Redis with a sliding window algorithm:

| Setting | Default | Description |
|---------|---------|-------------|
| `RATE_LIMIT_REQUESTS` | 10 | Maximum requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | 60 | Window duration in seconds |

### Rate-Limited Endpoints

The following endpoints are protected by rate limiting:

| Endpoint | Reason |
|----------|--------|
| `POST /api/v1/auth/login` | Prevent brute-force attacks |
| `POST /api/v1/auth/register` | Prevent account enumeration and spam |
| `POST /api/v1/ai/extract-recipe-from-url` | AI API costs money |
| `POST /api/v1/ai/extract-recipe-from-image` | AI API costs money |
| `GET /api/v1/ai/extract-recipe-stream` | AI API costs money |
| `GET /api/v1/ai/extract-recipe-image-stream` | AI API costs money |

### Bypass Paths

The following paths are **not** rate limited:

| Path | Reason |
|------|--------|
| `/api/v1/health` | Health checks for load balancers and monitoring |
| `/health` | Alternative health check path |

### Rate Limit Response

When the rate limit is exceeded, the API returns:

**HTTP Status**: `429 Too Many Requests`

**Response Headers**:

- `Retry-After`: Seconds until the rate limit resets
- `X-RateLimit-Limit`: Maximum requests allowed per window
- `X-RateLimit-Remaining`: Remaining requests in current window

**Response Body**:

```json
{
  "detail": "Too many requests. Please try again later."
}
```

### Development/Test Mode

If Upstash Redis is not configured (`UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are not set), rate limiting is **disabled**. This allows local development and testing without an Upstash account.

## OpenAPI

- Swagger UI: `/api/v1/docs`
- Redoc: `/api/v1/redoc`
