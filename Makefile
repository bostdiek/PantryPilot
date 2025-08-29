# Makefile for PantryPilot

.PHONY: help validate-env up up-dev up-prod down down-dev down-prod logs reset-db reset-db-dev reset-db-prod reset-db-volume db-backup db-restore db-maintenance db-shell lint lint-backend lint-frontend type-check type-check-backend type-check-frontend format format-backend format-frontend test test-backend test-frontend test-coverage install install-backend install-frontend check ci dev-setup clean migrate migrate-dev migrate-prod check-migrations clean-keep-db

# Environment detection
ENV ?= dev
COMPOSE_FILES = -f docker-compose.yml
ifeq ($(ENV),prod)
	COMPOSE_FILES += -f docker-compose.prod.yml
	ENV_FILE = .env.prod
else
	COMPOSE_FILES += -f docker-compose.dev.yml
	ENV_FILE = .env.dev
endif

help:
	@echo "Available targets:"
	@echo ""
	@echo "Docker Compose & Environment:"
	@echo "  validate-env       - Validate environment configuration"
	@echo "  up                 - Start all services (ENV=dev default, ENV=prod for production)"
	@echo "  up-dev             - Start development services"
	@echo "  up-prod            - Start production services"
	@echo "  down               - Stop services (respects ENV)"
	@echo "  down-dev           - Stop development services"
	@echo "  down-prod          - Stop production services"
	@echo "  logs               - View logs (ENV=dev default, ENV=prod for production)"
	@echo "  reset-db           - Reset database (respects ENV)"
	@echo "  reset-db-dev       - Reset development database"
	@echo "  reset-db-prod      - Reset production database"
	@echo "  reset-db-volume    - Remove ONLY the database volume and re-init (respects ENV)"
	@echo "  migrate            - Apply DB migrations (respects ENV)"
	@echo "  check-migrations   - Run Alembic upgrade on a temporary DB to validate migrations"
	@echo ""
	@echo "Database Management:"
	@echo "  db-backup          - Create database backup (ENV=dev default)"
	@echo "  db-restore FILE=   - Restore database from backup file"
	@echo "  db-maintenance CMD= - Run database maintenance (analyze, vacuum, stats, etc.)"
	@echo "  db-shell           - Open PostgreSQL shell (ENV=dev default)"
	@echo ""
	@echo "Development:"
	@echo "  dev               - Alias for 'up' (development)"
	@echo "  prod              - Alias for 'ENV=prod up' (production)"
	@echo "  install            - Install all dependencies"
	@echo "  install-backend    - Install backend dependencies"
	@echo "  install-frontend   - Install frontend dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint               - Run all linters"
	@echo "  lint-backend       - Run backend linter (Ruff)"
	@echo "  lint-frontend      - Run frontend linter (ESLint)"
	@echo "  type-check         - Run all type checkers"
	@echo "  type-check-backend - Run backend type checker (mypy)"
	@echo "  type-check-frontend- Run frontend type checker (tsc)"
	@echo "  format             - Format all code"
	@echo "  format-backend     - Format backend code (Ruff)"
	@echo "  format-frontend    - Format frontend code (Prettier)"
	@echo ""
	@echo "Testing:"
	@echo "  test               - Run all tests"
	@echo "  test-backend       - Run backend tests"
	@echo "  test-frontend      - Run frontend tests"
	@echo "  test-coverage      - Run backend tests with coverage report"
	@echo ""
	@echo "Cleanup and Maintenance:"
	@echo "  clean              - Stop services, remove containers (keeps DB volume), clear local caches"
	@echo "  clean-deps         - Remove dependency volumes and rebuild with fresh deps"
	@echo "  clean-build        - Remove build caches and rebuild everything from scratch"
	@echo "  clean-all          - Remove ALL project Docker resources (safe - PantryPilot only)"
	@echo "  clean-keep-db      - Remove containers and ALL project volumes except the Postgres data volume"
	@echo ""
	@echo "Usage Examples:"
	@echo "  make up              # Start in development mode"
	@echo "  make ENV=prod up     # Start in production mode"
	@echo "  make logs            # View development logs"
	@echo "  make ENV=prod logs   # View production logs"
	@echo "  make db-backup       # Backup development database"
	@echo "  make db-maintenance CMD=stats  # Show database statistics"
	@echo "  make clean-deps      # Fix dependency issues (like react-router-dom not found)"
	@echo "  make clean-build     # Rebuild everything from scratch"

# Environment and Docker Compose targets
validate-env:
	# Validate environment configuration
	# python scripts/validate-env.py

up: validate-env
	# Start services using Docker Compose (ENV=$(ENV))
	@echo "🚀 Starting PantryPilot in $(ENV) mode..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) up -d
	@echo "✅ Services started! Check 'make logs' for output."
	@echo "⏳ Waiting for database to become ready and running Alembic migrations..."
	@/bin/sh -lc 'set -eu; \
	  if [ -f "$(ENV_FILE)" ]; then set -a; . "$(ENV_FILE)"; set +a; fi; \
	  ATTEMPTS=30; \
	  until docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) exec -T db pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB >/dev/null 2>&1; do \
	    ATTEMPTS=$$((ATTEMPTS-1)); \
	    if [ $$ATTEMPTS -le 0 ]; then echo "❌ DB not ready"; exit 1; fi; \
	    sleep 2; \
	  done; \
	  echo "✅ DB is ready. Applying migrations..."; \
	  docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) exec -T backend sh -lc "uv run alembic -c /app/src/alembic.ini upgrade head"; \
	  echo "✅ Migrations up-to-date."'

up-dev:
	# Start development services
	$(MAKE) ENV=dev up

up-prod:
	# Start production services
	$(MAKE) ENV=prod up

down:
	# Stop services (ENV=$(ENV))
	@echo "🛑 Stopping PantryPilot services..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) down

down-dev:
	# Stop development services
	$(MAKE) ENV=dev down

down-prod:
	# Stop production services
	$(MAKE) ENV=prod down

logs:
	# View logs (ENV=$(ENV))
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) logs -f

reset-db:
	# Reset database: stop, remove volumes, and start fresh (ENV=$(ENV))
	@echo "🗄️ Resetting database in $(ENV) mode..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) down -v
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) up -d db
	@echo "✅ Database reset complete!"

# Remove ONLY the Postgres data volume and reinitialize DB (ENV=dev default)
reset-db-volume:
	# Stop and remove only the db service container to free the volume
	@echo "Removing ONLY Postgres data volume for $(ENV) environment..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) stop db >/dev/null 2>&1 || true
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) rm -f db >/dev/null 2>&1 || true
	# Compute volume name and remove it
	@/bin/sh -lc 'set -eu; \
	  if [ -f "$(ENV_FILE)" ]; then set -a; . "$(ENV_FILE)"; set +a; fi; \
	  VOL_NAME="$${COMPOSE_PROJECT_NAME:-$$(basename "$$PWD")}_postgres_data"; \
	  echo "Target volume: $$VOL_NAME"; \
	  docker volume rm "$$VOL_NAME" >/dev/null 2>&1 || echo "Info: volume $$VOL_NAME not found or already removed"; \
	  echo "Starting fresh db to re-run init scripts..."; \
	  true'
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) up -d db
	@echo "DB volume removed and re-initialized for $(ENV) environment."

reset-db-dev:
	# Reset development database
	$(MAKE) ENV=dev reset-db

reset-db-prod:
	# Reset production database
	$(MAKE) ENV=prod reset-db

# Installation targets
install: install-backend install-frontend

install-backend:
	# Install backend dependencies
	cd apps/backend && uv sync

install-frontend:
	# Install frontend dependencies
	cd apps/frontend && npm ci

# Linting targets
lint: lint-backend lint-frontend

lint-backend:
	# Run backend linter
	cd apps/backend && uv run ruff check .

lint-frontend:
	# Run frontend linter
	cd apps/frontend && npm run lint

# Type checking targets
type-check: type-check-backend type-check-frontend

type-check-backend:
	# Run backend type checker
	# Run backend type checker (use MYPYPATH=src so mypy resolves runtime package names)
	cd apps/backend && MYPYPATH=src uv run mypy -p api -p core -p crud -p dependencies -p models -p schemas

type-check-frontend:
	# Run frontend type checker
	cd apps/frontend && npm run type-check

# Formatting targets
format: format-backend format-frontend

format-backend:
	# Format backend code
	cd apps/backend && uv run ruff format .

format-frontend:
	# Format frontend code
	cd apps/frontend && npm run format

# Testing targets
test: test-backend test-frontend

test-backend:
	# Run backend tests
	cd apps/backend && uv run pytest

test-frontend:
	# Run frontend tests
	cd apps/frontend && npm test -- --run

test-coverage:
	# Run backend tests with coverage
	cd apps/backend && uv run pytest --cov=src --cov-report=term --cov-report=html

# Convenience targets
check: lint type-check check-migrations
	# Run all code quality checks

ci: install check test
	# Run full CI pipeline locally

dev-setup: install
	# Set up development environment
	cd apps/backend && uv run pre-commit install

# Short aliases
dev: up
prod:
	$(MAKE) ENV=prod up

# Database management targets
db-backup:
	# Create database backup (ENV=$(ENV))
	@echo "🗄️ Creating database backup for $(ENV) environment..."
	./db/backup.sh -e $(ENV)

db-restore:
	# Restore database from backup file (ENV=$(ENV), FILE=backup.sql)
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Error: FILE parameter required. Usage: make db-restore FILE=backup.sql"; \
		exit 1; \
	fi
	@echo "🔄 Restoring database from $(FILE) to $(ENV) environment..."
	./db/restore.sh -e $(ENV) $(FILE)

db-maintenance:
	# Run database maintenance command (ENV=$(ENV), CMD=stats)
	@if [ -z "$(CMD)" ]; then \
		echo "❌ Error: CMD parameter required. Usage: make db-maintenance CMD=stats"; \
		echo "Available commands: analyze, vacuum, stats, health, slow-queries, connections, size, all"; \
		exit 1; \
	fi
	@echo "🔧 Running database maintenance: $(CMD) on $(ENV) environment..."
	./db/maintenance.sh -e $(ENV) $(CMD)

db-shell:
	# Open PostgreSQL shell (ENV=$(ENV))
	@echo "🐘 Opening PostgreSQL shell for $(ENV) environment..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) exec db psql -U $$POSTGRES_USER -d $$POSTGRES_DB

# Apply Alembic migrations on demand
migrate:
	# Apply database migrations (ENV=$(ENV))
	@echo "📦 Applying Alembic migrations for $(ENV) environment..."
	@/bin/sh -lc 'set -eu; \
	  if [ -f "$(ENV_FILE)" ]; then set -a; . "$(ENV_FILE)"; set +a; fi; \
	  ATTEMPTS=30; \
	  until docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) exec -T db pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB >/dev/null 2>&1; do \
	    ATTEMPTS=$$((ATTEMPTS-1)); \
	    if [ $$ATTEMPTS -le 0 ]; then echo "❌ DB not ready"; exit 1; fi; \
	    sleep 2; \
	  done; \
	  docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) exec -T backend sh -lc "uv run alembic -c /app/src/alembic.ini upgrade head"; \
	  echo "✅ Migrations up-to-date."'

migrate-dev:
	# Apply database migrations for development environment
	$(MAKE) ENV=dev migrate

migrate-prod:
	# Apply database migrations for production environment
	$(MAKE) ENV=prod migrate

check-migrations:
	# Validate Alembic migrations by applying to a temporary database
	@chmod +x scripts/check_migrations.sh >/dev/null 2>&1 || true
	@/bin/sh scripts/check_migrations.sh "$(ENV_FILE)" "$(COMPOSE_FILES)"

# =============================================================================
# Cleanup and Maintenance Commands
# =============================================================================

clean:
	# Stop all services and remove containers (keep named volumes like DB)
	@echo "🧹 Stopping services and cleaning up Docker containers for $(ENV) environment..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) down --remove-orphans
	# Clear local caches/artifacts
	cd apps/backend && rm -rf .pytest_cache __pycache__ .coverage htmlcov .mypy_cache .ruff_cache
	cd apps/frontend && rm -rf node_modules/.cache dist coverage
	@echo "🗑️ Removing project dangling images..."
	docker images --filter "dangling=true" --filter "reference=pantrypilot*" -q | xargs -r docker rmi
	@echo "✅ Cleanup complete!"

clean-deps:
	# Remove dependency volumes and rebuild with fresh dependencies (keep DB volume)
	@echo "🧹 Cleaning dependency volumes for $(ENV) environment..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) down --remove-orphans
	@echo "📦 Removing frontend dependency volume..."
	docker volume rm $$(docker volume ls -q | grep frontend_node_modules) 2>/dev/null || true
	@echo "📦 Removing backend venv cache volume..."
	docker volume rm $$(docker volume ls -q | grep backend_cache) 2>/dev/null || true
	@echo "🔄 Rebuilding with fresh dependencies..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) build --no-cache frontend
	@echo "🚀 Starting services with clean dependencies..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) up -d
	@echo "✅ Dependencies refreshed!"

clean-build:
	# Remove all build caches and rebuild everything from scratch (keep DB volume)
	@echo "🧹 Cleaning all Docker build caches and images for $(ENV) environment..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) down --remove-orphans
	@echo "🗑️ Removing project build cache..."
	docker builder prune -f --filter "label=project=pantrypilot" 2>/dev/null || docker builder prune -f --filter "unused-for=1h"
	@echo "🗑️ Removing all project images..."
	docker images "pantrypilot*" -q | xargs -r docker rmi -f
	@echo "🔄 Rebuilding everything from scratch..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) build --no-cache
	@echo "✅ Clean rebuild complete!"

clean-all:
	# Remove all project-related Docker resources (safe - only affects PantryPilot)
	@echo "🧹 Cleaning all PantryPilot Docker resources for $(ENV) environment..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) down --volumes --remove-orphans
	@echo "🗑️ Removing all project volumes..."
	docker volume ls -q | grep -E "(pantrypilot|frontend_node_modules)" | xargs -r docker volume rm
	@echo "🗑️ Removing all project images..."
	docker images --filter "reference=pantrypilot*" -q | xargs -r docker rmi -f
	@echo "🗑️ Removing project build cache..."
	docker builder prune -f --filter "label=project=pantrypilot"
	@echo "✅ All PantryPilot Docker resources cleaned!"

# Remove all project containers and non-DB volumes, preserving Postgres data volume
clean-keep-db:
	@echo "🧹 Cleaning containers and non-DB volumes for $(ENV) environment..."
	# Stop and remove containers (keep volumes for now)
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) down --remove-orphans
	# Determine compose project name and Postgres data volume
	@/bin/sh -lc 'set -eu; \
	  if [ -f "$(ENV_FILE)" ]; then set -a; . "$(ENV_FILE)"; set +a; fi; \
	  PNAME="$${COMPOSE_PROJECT_NAME:-$$(basename "$$PWD")}"; \
	  DB_VOL="$${PNAME}_postgres_data"; \
	  echo "Keeping DB volume: $$DB_VOL"; \
	  echo "Removing project volumes except DB..."; \
	  for v in $$(docker volume ls --format "{{.Name}}" | grep "^$${PNAME}_" || true); do \
	    if [ "$$v" != "$$DB_VOL" ]; then echo " - removing $$v"; docker volume rm -f "$$v" >/dev/null 2>&1 || true; fi; \
	  done; \
	  true'
	@echo "🔄 Rebuilding frontend to refresh npm deps (no cache)..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) build --no-cache frontend
	@echo "🚀 Starting services..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) up -d
	@echo "✅ Containers restarted; non-DB volumes removed; DB preserved."
