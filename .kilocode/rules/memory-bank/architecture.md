# Architecture

## Runtime topology (Docker Compose)
PantryPilot runs via Docker Compose with environment-specific overlays. The environment is selected by the ENV make variable: dev (default) or prod. Compose files include a base file plus an environment-specific file, and the corresponding .env.* file is loaded for variables.

- Base compose file: docker-compose.yml
- Dev overlay: docker-compose.dev.yml
- Prod overlay: docker-compose.prod.yml
- Env files: .env.dev or .env.prod

Services (names referenced by Makefile targets):
- backend: FastAPI app container; runs migrations and app process
- db: PostgreSQL
- frontend: Vite/React dev or built app (depending on environment)

## Startup flow (make up)
make up performs:
1. docker compose up -d using the selected env file and compose files
2. Waits for db readiness using pg_isready inside the db service
3. Runs Alembic migrations inside the backend container:
   uv run alembic -c /app/src/alembic.ini upgrade head

This ensures database schema is current on every start.

Aliases:
- make dev → make up (ENV=dev)
- make prod → make ENV=prod up
- make logs streams aggregated service logs; make down stops services respecting ENV

## On-demand migrations
make migrate repeats the readiness check and runs the same Alembic upgrade in the backend container. Convenience wrappers exist: make migrate-dev and make migrate-prod.

## Database lifecycle and preservation strategy
- make reset-db: compose down -v, then start db fresh
- make reset-db-dev / reset-db-prod: environment-specific wrappers
- make reset-db-volume: removes only the Postgres data volume, then starts db to re-run init scripts
  - Volume naming strategy:
    - Project name PNAME is COMPOSE_PROJECT_NAME if set, else the basename of the repo directory
    - Preserved DB volume name is PNAME_postgres_data
- make clean-keep-db: removes containers and all project volumes except the DB volume, rebuilds frontend without cache, and restarts services

## Database operations scripts
- Backups: make db-backup runs ./db/backup.sh -e ENV
- Restore: make db-restore FILE=path/to/backup.sql runs ./db/restore.sh -e ENV FILE
- Maintenance: make db-maintenance CMD=stats runs ./db/maintenance.sh -e ENV CMD
  - Supported maintenance commands: analyze, vacuum, stats, health, slow-queries, connections, size, all
- Shell: make db-shell opens psql in the db container using POSTGRES_USER and POSTGRES_DB from the env file

## Code quality and CI workflow
- Linting: make lint → backend (Ruff) and frontend (ESLint)
- Type checking: make type-check → backend (mypy with MYPYPATH=src and specific packages) and frontend (tsc)
- Formatting: make format → backend (ruff format) and frontend (prettier)
- Testing: make test runs backend (pytest) and frontend (npm test -- --run); make test-coverage runs backend coverage to terminal and HTML
- Aggregate checks: make check runs lint, type-check, and check-migrations; make ci runs install, check, and test

## Developer setup
- make install installs backend deps via uv sync and frontend deps via npm ci
- make dev-setup also installs pre-commit hooks in the backend container context
- create-dev-user target executes the script inside the backend container to create an idempotent development user

## File and path references
- Alembic configuration: apps/backend/src/alembic.ini
- Backend tests: apps/backend/tests/
- DB scripts: db/backup.sh, db/restore.sh, db/maintenance.sh
- Migration check script: scripts/check_migrations.sh

Notes
- Python commands are run inside containers via uv, ensuring toolchain consistency
- Compose operations consistently pass both the env file and compose files, so manual docker compose commands should mimic that for parity
