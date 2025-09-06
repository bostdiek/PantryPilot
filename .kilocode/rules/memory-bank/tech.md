# Tech

## Stacks and Versions
- Backend (Python 3.12)
  - FastAPI ≥ 0.116.1, Uvicorn/Gunicorn
  - SQLAlchemy ≥ 2.x + asyncpg
  - Alembic ≥ 1.16
  - Auth: python-jose + Argon2
  - Settings: pydantic-settings
  - Dev/Test: pytest, pytest-asyncio, httpx, mypy, ruff
  - Manifest: [pyproject.toml](apps/backend/pyproject.toml)
- Frontend (TypeScript 5.8, Node ecosystem)
  - React 19, React Router 7, Zustand 5
  - Vite 7, Tailwind CSS 4
  - Vitest 3 + Testing Library
  - Manifest: [package.json](apps/frontend/package.json)
- Infra/Tooling
  - Dockerfiles for backend and frontend
  - CI: Coverage to Codecov (see README)
  - Linters/formatters: Ruff, mypy, ESLint, Prettier
  - Configs: [apps/backend/mypy.ini](apps/backend/mypy.ini), [apps/frontend/.eslintrc.cjs](apps/frontend/.eslintrc.cjs), [apps/frontend/.prettierignore](apps/frontend/.prettierignore)

## Dev Setup and Commands
- Docker Compose and environments
  - ENV selects environment: dev (default) or prod. Compose files: docker-compose.yml plus docker-compose.dev.yml or docker-compose.prod.yml; env file: .env.dev or .env.prod.
  - make up runs docker compose up -d, waits for DB readiness (pg_isready), then applies Alembic migrations inside the backend container via uv run alembic -c /app/src/alembic.ini upgrade head.
  - Aliases: dev is an alias for up; prod runs ENV=prod up. logs streams aggregated service logs; down respects ENV.
- Make targets (grouped overview)
  - Environment and Compose: validate-env, up, up-dev, up-prod, down, down-dev, down-prod, logs
  - Database lifecycle: reset-db, reset-db-dev, reset-db-prod, reset-db-volume
  - Database management: db-backup, db-restore FILE=..., db-maintenance CMD=..., db-shell
  - Migrations: migrate, migrate-dev, migrate-prod, check-migrations (runs [check_migrations.sh](scripts/check_migrations.sh))
  - Installation and setup: install, install-backend (uv sync), install-frontend (npm ci), dev-setup (uv run pre-commit install)
  - Code quality: lint, lint-backend (uv run ruff check .), lint-frontend (npm run lint), type-check, type-check-backend (MYPYPATH=src uv run mypy -p api -p core -p crud -p dependencies -p models -p schemas), type-check-frontend (npm run type-check), format, format-backend (uv run ruff format .), format-frontend (npm run format), check, ci
  - Testing: test, test-backend (uv run pytest), test-frontend (npm test -- --run), test-coverage (uv run pytest --cov=src --cov-report=term --cov-report=html)
  - Convenience: dev, prod, create-dev-user (executes [create_dev_user.py](apps/backend/scripts/create_dev_user.py) inside backend container)
- DB scripts and usage examples
  - Backups: make db-backup
  - Restore: make db-restore FILE=path/to/backup.sql
  - Maintenance: make db-maintenance CMD=stats (available: analyze, vacuum, stats, health, slow-queries, connections, size, all)
  - Shell: make db-shell to open psql against configured DB
- Cleanup and maintenance
  - clean: compose down --remove-orphans; clear caches in apps/backend and apps/frontend; remove dangling Docker images matching pantrypilot*.
  - clean-deps: stop containers, remove frontend_node_modules and backend_cache volumes, rebuild frontend without cache, keep DB volume, then up -d.
  - clean-build: full rebuild from scratch; prunes builder cache labeled project=pantrypilot, removes pantrypilot* images, rebuilds all.
  - clean-all: down with volumes, remove all project volumes matching pantrypilot or frontend_node_modules, remove images/reference pantrypilot*, prune builder cache.
  - clean-keep-db: preserves the Postgres data volume {COMPOSE_PROJECT_NAME or basename}_postgres_data while removing other project volumes; rebuilds frontend without cache; restarts services.
- Tooling notes
  - Python commands run inside containers using uv; Alembic config at [alembic.ini](apps/backend/src/alembic.ini).
  - Frontend scripts live in [package.json](apps/frontend/package.json); backend test config in [pyproject.toml](apps/backend/pyproject.toml).
- Quick commands
  - make up
  - make ENV=prod up
  - make logs
  - make ENV=prod logs
  - make db-maintenance CMD=stats
  - make clean-deps
  - make clean-build

## API and Auth
- Base: /api/v1; documented in [docs/API_DESIGN.md](docs/API_DESIGN.md)
- OAuth2 password flow; bearer JWTs
  - Token creation: [create_access_token()](apps/backend/src/core/security.py:19)
  - Token decoding: [decode_token()](apps/backend/src/core/security.py:51)
  - Current user dependency: [get_current_user()](apps/backend/src/dependencies/auth.py:39)
- Wrapped responses on most endpoints via ApiResponse

## State, Routing, and Data Loading (Frontend)
- Router and loaders: [routerConfig.tsx](apps/frontend/src/routerConfig.tsx)
- Auth persistence and hydration flag: [useAuthStore](apps/frontend/src/stores/useAuthStore.ts)
- API client and error handling: [api/client.ts](apps/frontend/src/api/client.ts)

## Database and Migrations
- Async engine/session dependency: [dependencies/db.py](apps/backend/src/dependencies/db.py)
- Alembic environment: [alembic/env.py](apps/backend/src/alembic/env.py)
- Representative migrations:
  - Initial schema: [20250827_00_initial_schema.py](apps/backend/src/alembic/versions/20250827_00_initial_schema.py)
  - Ownership/admin role: [20250905_05_add_user_ownership_and_admin_role.py](apps/backend/src/alembic/versions/20250905_05_add_user_ownership_and_admin_role.py)

## Environment Variables (from [.env.example](.env.example))
- DB
  - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT
  - DATABASE_URL (backend uses asyncpg)
- FastAPI
  - ENVIRONMENT, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
  - API_V1_STR, PROJECT_NAME, VERSION
- CORS
  - CORS_ORIGINS (CSV or JSON array string)
- Frontend
  - VITE_API_URL (defaults to http://localhost:8000 in dev/test)
- Ops
  - COMPOSE_PROJECT_NAME, LOG_LEVEL, SENTRY_DSN (optional), CSP_* (prod)

## Testing Strategy
- Backend
  - Unit/integration tests in [apps/backend/tests/](apps/backend/tests)
  - pytest with asyncio and httpx clients; coverage gathered in CI
- Frontend
  - Vitest + Testing Library; jsdom environment
  - Coverage via vitest V8 provider; see scripts in [package.json](apps/frontend/package.json)

## External Integrations
- None required at runtime beyond PostgreSQL
- Sentry DSN placeholder in env template (TBD if used)
