# API Design

Base prefix: `/api/v1`
Versioning: Path-based (`/api/v{n}`) with option to add header versioning later.
Response envelope: `ApiResponse<T>` with `success`, `data`, `message`, `error`.

## Endpoints (v1)

- GET `/api/v1/health` — health check
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

## Schemas

- See `apps/backend/src/schemas/*` for Pydantic models with strict validation.
- Shared enums: `RecipeDifficulty`, `RecipeCategory`.

## Pagination

- Offset/limit parameters; response returns `{ items, limit, offset, total }`.

## Errors

- Standardized error shape via `ApiResponse` with `success=false` and `error` object.

## OpenAPI

- Swagger UI: `/api/v1/docs`
- Redoc: `/api/v1/redoc`
