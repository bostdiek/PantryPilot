# Deployment & Local Development Guide

This project uses Docker Compose with environment-specific overrides and a Makefile for common workflows.

## Prerequisites

- Docker Desktop: <https://www.docker.com/products/docker-desktop/>
- uv (Python package & env manager): <https://docs.astral.sh/uv/>
- Node.js & npm: <https://nodejs.org/> and <https://docs.npmjs.com/>

These tools let you run the full stack locally and work on backend (Python) and frontend (React) code.

## Local Development (Docker Compose)

- Start services (development): `make dev` (uses `.env.dev` + `docker-compose.dev.yml`)
- Start services (production): `make prod` (alias for `ENV=prod make up`, uses `.env.prod` + `docker-compose.prod.yml`)
- View logs: `make logs`
- Stop services: `make down`

Notes:

- Backend API is exposed under `/api/v1`. Swagger UI is available at `/api/v1/docs` and Redoc at `/api/v1/redoc`.
- Database migrations run automatically during startup; see below for manual control.

## Database Migrations

- Apply migrations (current ENV): `make migrate`
- Validate Alembic migrations on a temporary DB: `make check-migrations`
- Reset development DB (destructive): see `make reset-db` targets in the Makefile.

## Code Quality & Tests (local)

You can run these from the project root via Makefile shortcuts:

- Lint all: `make lint`
- Type-check all: `make type-check`
- Tests (backend + frontend): `make test`
- Backend coverage (HTML at `apps/backend/htmlcov/index.html`): use the VS Code task "Test: Run with Coverage" or run the backend coverage command directly.

Backend-only (optional, via uv):

- Lint: `cd apps/backend && uv run ruff check .`
- Type-check: `cd apps/backend && uv run mypy -p api -p core -p crud -p dependencies -p models -p schemas`
- Tests: `cd apps/backend && uv run pytest`

Frontend-only (optional, via npm):

- Type-check: `cd apps/frontend && npm run type-check`
- Tests: `cd apps/frontend && npm test`

## Images & Runtime

- Backend image: multi-stage with `uv` and `gunicorn+uvicorn` workers
- Frontend image: Vite static build served behind Nginx
- Reverse proxy: Nginx configuration in `nginx/`

## Environment Configuration

- Set `CORS_ORIGINS` appropriately (e.g., dev `http://localhost:5173`)
- Configure database credentials in `.env.dev` and `.env.prod`

See the root `README.md` for an overview and quick-start commands, and `docs/API_DESIGN.md` for API details.
