# Makefile for PantryPilot

.PHONY: help validate-env up up-dev up-prod down down-dev down-prod logs reset-db reset-db-dev reset-db-prod reset-db-volume db-backup db-restore db-maintenance db-shell lint lint-backend lint-frontend type-check type-check-backend type-check-frontend format format-backend format-frontend test test-backend test-frontend test-coverage secrets-scan secrets-audit secrets-update install install-backend install-frontend check ci dev-setup clean migrate migrate-dev migrate-prod check-migrations backfill-embeddings backfill-embeddings-dry-run backfill-embeddings-local backfill-embeddings-local-dry-run clean-keep-db lan-ip frontend-lan backend-lan dev-lan dev-lan-docker check-node test-frontend-docker test-frontend-coverage-docker

# Image / build targets (added)
.PHONY: build-frontend build-backend build-all build-prod-frontend build-prod-backend build-prod-all buildx-setup buildx-push

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
	@echo "  backfill-embeddings - Backfill embeddings for recipes (Docker, local dev)"
	@echo "  backfill-embeddings-dry-run - Show recipes needing embeddings (Docker, local dev)"
	@echo "  backfill-embeddings-local - Backfill embeddings (direct execution, for cloud)"
	@echo "  backfill-embeddings-local-dry-run - Show recipes needing embeddings (direct, for cloud)"
	@echo ""
	@echo "Development:"
	@echo "  dev               - Alias for 'up' (development)"
	@echo "  prod              - Alias for 'ENV=prod up' (production)"
	@echo "  lan-ip            - Print local LAN IP + URLs for phone testing"
	@echo "  backend-lan        - Run backend locally on 0.0.0.0:8000 (LAN accessible)"
	@echo "  frontend-lan       - Run frontend locally on 0.0.0.0:5173 (LAN accessible)"
	@echo "  dev-lan            - Run backend-lan + frontend-lan together (local, for mobile testing)"
	@echo "  dev-lan-docker     - Run Docker dev stack with LAN/mobile-friendly URLs (phone testing)"
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
	@echo "Security:"
	@echo "  secrets-scan       - Run secret scanning with detect-secrets"
	@echo "  secrets-audit      - Audit secrets baseline and show statistics"
	@echo "  secrets-update     - Update secrets baseline (after resolving findings)"
	@echo ""
	@echo "Testing:"
	@echo "  test               - Run all tests"
	@echo "  test-backend       - Run backend tests"
	@echo "  test-frontend      - Run frontend tests"
	@echo "  test-frontend-docker - Run frontend tests via Docker (Node 24 container)"
	@echo "  test-frontend-coverage-docker - Run frontend tests with coverage via Docker"
	@echo "  test-coverage      - Run backend tests with coverage report"
	@echo ""
	@echo "Cleanup and Maintenance:"
	@echo "  clean              - Stop services, remove containers (keeps DB volume), clear local caches"
	@echo "  clean-deps         - Remove dependency volumes and rebuild with fresh deps"
	@echo "  clean-build        - Remove build caches and rebuild everything from scratch"
	@echo "  clean-all          - Remove ALL project Docker resources (safe - PantryPilot only)"
	@echo "  clean-keep-db      - Remove containers and ALL project volumes except the Postgres data volume"
	@echo ""
	@echo "Image Build & Distribution:"
	@echo "  build-frontend           - Build dev frontend image"
	@echo "  build-backend            - Build dev backend image"
	@echo "  build-all                - Build all dev images"
	@echo "  build-prod-frontend      - Build prod frontend image (embeds VITE_API_URL)"
	@echo "  build-prod-backend       - Build prod backend image"
	@echo "  build-prod-all           - Build all prod images"
	@echo "  buildx-setup             - Create/ensure Docker Buildx builder for multi-arch"
	@echo "  buildx-push              - Multi-arch build & push (set REGISTRY, IMAGE_NAMESPACE, VERSION)"
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
	@echo "  make dev-lan         # Start local LAN-accessible dev servers (phone testing)"

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
	  ENV_ABS="$(abspath $(ENV_FILE))"; \
	  if [ -f "$$ENV_ABS" ]; then echo "Sourcing env: $$ENV_ABS"; set -a; . "$$ENV_ABS"; set +a; else echo "⚠️  Env file not found at $$ENV_ABS"; fi; \
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

check-node:
	@/bin/sh scripts/check-node.sh

install-frontend: check-node
	# Install frontend dependencies
	cd apps/frontend && npm ci

# Linting targets
lint: lint-backend lint-frontend

lint-backend:
	# Run backend linter
	cd apps/backend && uv run ruff check .

lint-frontend: check-node
	# Run frontend linter
	cd apps/frontend && npm run lint

# Type checking targets
type-check: type-check-backend type-check-frontend

type-check-backend:
	# Run backend type checker
	# Run backend type checker (use MYPYPATH=src so mypy resolves runtime package names)
	cd apps/backend && MYPYPATH=src uv run mypy -p api -p core -p crud -p dependencies -p models -p schemas

type-check-frontend: check-node
	# Run frontend type checker
	cd apps/frontend && npm run type-check

# Formatting targets
format: format-backend format-frontend

format-backend:
	# Format backend code
	cd apps/backend && uv run ruff format .

format-frontend: check-node
	# Format frontend code
	cd apps/frontend && npm run format

# LAN / mobile testing (local dev servers; nginx not required)
lan-ip:
	@/bin/sh -lc 'set -eu; \
	  IP="$$(ipconfig getifaddr en0 2>/dev/null || true)"; \
	  if [ -z "$$IP" ]; then IP="$$(ipconfig getifaddr en1 2>/dev/null || true)"; fi; \
	  if [ -z "$$IP" ]; then echo "Could not determine LAN IP (en0/en1)."; exit 1; fi; \
	  echo "LAN IP: $$IP"; \
	  echo "Frontend: http://$$IP:5173"; \
	  echo "Backend:  http://$$IP:8000/api/v1/health"; \
	  echo "Tip: ensure phone + Mac are on the same Wi-Fi."'

backend-lan:
	@/bin/sh -lc 'set -eu; \
	  IP="$$(ipconfig getifaddr en0 2>/dev/null || true)"; \
	  if [ -z "$$IP" ]; then IP="$$(ipconfig getifaddr en1 2>/dev/null || true)"; fi; \
	  if [ -z "$$IP" ]; then echo "Could not determine LAN IP (en0/en1)."; exit 1; fi; \
	  echo "Starting backend on 0.0.0.0:8000 (LAN accessible)"; \
	  echo "Allowing CORS from http://$$IP:5173"; \
	  export ENVIRONMENT=development; \
	  export CORS_ORIGINS="http://$$IP:5173,http://localhost:5173,http://127.0.0.1:5173"; \
	  export FRONTEND_URL="http://$$IP:5173"; \
	  cd apps/backend && PYTHONPATH=./src uv run fastapi dev src/main.py --host 0.0.0.0 --port 8000'

frontend-lan: check-node
	@/bin/sh -lc 'set -eu; \
	  IP="$$(ipconfig getifaddr en0 2>/dev/null || true)"; \
	  if [ -z "$$IP" ]; then IP="$$(ipconfig getifaddr en1 2>/dev/null || true)"; fi; \
	  if [ -z "$$IP" ]; then echo "Could not determine LAN IP (en0/en1)."; exit 1; fi; \
	  echo "Starting frontend on 0.0.0.0:5173 (LAN accessible)"; \
	  echo "Using VITE_API_URL=http://$$IP:8000"; \
	  export VITE_API_URL="http://$$IP:8000"; \
	  cd apps/frontend && npm run dev -- --host 0.0.0.0 --port 5173'

dev-lan:
	@echo "Starting local LAN-accessible dev servers (backend + frontend)."
	@echo "Note: output may interleave; stop with Ctrl+C."
	$(MAKE) -j2 backend-lan frontend-lan

# LAN / mobile testing (Docker Compose dev stack)
dev-lan-docker:
	@/bin/sh -lc 'set -eu; \
	  IP="$$(ipconfig getifaddr en0 2>/dev/null || true)"; \
	  if [ -z "$$IP" ]; then IP="$$(ipconfig getifaddr en1 2>/dev/null || true)"; fi; \
	  if [ -z "$$IP" ]; then echo "Could not determine LAN IP (en0/en1)."; exit 1; fi; \
	  echo "Starting Docker dev stack for mobile testing..."; \
	  echo "Frontend: http://$$IP:5173"; \
	  echo "Backend:  http://$$IP:8000/api/v1/health"; \
	  echo "Using VITE_API_URL=http://$$IP:8000"; \
	  echo "Allowing CORS from http://$$IP:5173"; \
	  VITE_API_URL="http://$$IP:8000" \
	  VITE_HMR_HOST="$$IP" \
	  FRONTEND_URL="http://$$IP:5173" \
	  CORS_ORIGINS="http://$$IP:5173,http://localhost:5173,http://127.0.0.1:5173" \
	    $(MAKE) ENV=dev up; \
	  echo "✅ Ready. Open http://$$IP:5173 on your phone."'

# Testing targets
test: test-backend test-frontend

test-backend:
	# Run backend tests
	cd apps/backend && uv run pytest

test-frontend: check-node
	# Run frontend tests
	cd apps/frontend && npm test -- --run

test-frontend-docker:
	# Run frontend tests via Docker Compose (uses Node 24 from apps/frontend/Dockerfile)
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) build frontend
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) run --rm --no-deps frontend npm test -- --run

test-frontend-coverage-docker:
	# Run frontend tests with coverage via Docker Compose
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) build frontend
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) run --rm --no-deps frontend npm run test:coverage -- --run

test-coverage:
	# Run backend tests with coverage
	cd apps/backend && uv run pytest --cov=src --cov-report=term --cov-report=html

# Security targets
secrets-scan:
	# Run secret scanning with detect-secrets
	cd apps/backend && uv run detect-secrets scan --baseline ../../.secrets.baseline --all-files ../..

secrets-audit:
	# Audit secrets baseline and show statistics
	cd apps/backend && uv run detect-secrets audit --stats ../../.secrets.baseline

secrets-update:
	# Update secrets baseline (run after resolving findings)
	cd apps/backend && uv run detect-secrets scan --baseline ../../.secrets.baseline --update ../..
	@echo "⚠️  Remember to review and commit the updated .secrets.baseline file"

# Create a development user in the backend DB (idempotent). Run inside backend container.
.PHONY: create-dev-user
create-dev-user:
	@echo "Creating dev user in backend DB..."
	# The backend container mounts the backend source at /app, so the script
	# is available at /app/scripts/create_dev_user.py inside the container.
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) exec -T backend sh -lc "uv run python /app/scripts/create_dev_user.py"


# Convenience targets
check: lint type-check check-migrations
	# Run all code quality checks

ci: install check test
	# Run full CI pipeline locally

dev-setup: install
	# Set up development environment
	cd apps/backend && uv run pre-commit install

# -----------------------------------------------------------------------------
# Image build helpers (local single-arch)
# -----------------------------------------------------------------------------
build-frontend:
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) build frontend

build-backend:
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) build backend

build-all: build-frontend build-backend

# Explicit production builds (ENV overridden to prod to pick prod overrides)
build-prod-frontend:
	$(MAKE) ENV=prod build-frontend

build-prod-backend:
	$(MAKE) ENV=prod build-backend

build-prod-all:
	$(MAKE) ENV=prod build-all

# -----------------------------------------------------------------------------
# Multi-arch builds & push via buildx
# Usage example:
#   make buildx-setup
#   REGISTRY=ghcr.io IMAGE_NAMESPACE=youruser VERSION=1.0.0 make buildx-push
# Requires: docker login to registry performed beforehand.
# -----------------------------------------------------------------------------
buildx-setup:
	@docker buildx inspect pantrypilot-builder >/dev/null 2>&1 || docker buildx create --use --name pantrypilot-builder
	@docker buildx use pantrypilot-builder
	@echo "✅ Buildx builder ready"

buildx-push: buildx-setup
	@if [ -z "$(REGISTRY)" ] || [ -z "$(IMAGE_NAMESPACE)" ] || [ -z "$(VERSION)" ]; then \
	  echo "❌ REGISTRY, IMAGE_NAMESPACE and VERSION must be set. Example:"; \
	  echo "   REGISTRY=ghcr.io IMAGE_NAMESPACE=myorg VERSION=0.1.0 make buildx-push"; \
	  exit 1; \
	fi
	@echo "🚀 Building & pushing multi-arch images: $(REGISTRY)/$(IMAGE_NAMESPACE)/pantrypilot-frontend:$(VERSION) and backend"
	docker buildx build \
	  --platform linux/amd64,linux/arm64 \
	  -f apps/frontend/Dockerfile \
	  --build-arg VITE_API_URL=$${VITE_API_URL:-http://localhost:8000} \
	  -t $(REGISTRY)/$(IMAGE_NAMESPACE)/pantrypilot-frontend:$(VERSION) \
	  --push apps/frontend
	docker buildx build \
	  --platform linux/amd64,linux/arm64 \
	  -f apps/backend/Dockerfile \
	  -t $(REGISTRY)/$(IMAGE_NAMESPACE)/pantrypilot-backend:$(VERSION) \
	  --push apps/backend
	@echo "✅ Multi-arch images pushed"

# Short aliases
dev: up
prod:
	$(MAKE) ENV=prod up

# Fix permissions on the nginx cache docker volume (one-time on host)
# Usage: `make fix-nginx-cache-perms` — requires sudo to change host volume dir perms
.PHONY: fix-nginx-cache-perms
fix-nginx-cache-perms:
	@echo "🔧 Fixing nginx cache volume permissions (requires sudo)..."
	@/bin/sh -lc '\
	  VOL=$$(docker volume ls --format "{{.Name}}" | grep -E "pantrypilot_nginx_cache|nginx_cache" | head -n1) || true; \
	  if [ -z "$$VOL" ]; then echo "ℹ️  No nginx cache volume found (skipping)"; exit 0; fi; \
	  MP=$$(docker volume inspect $$VOL -f "{{.Mountpoint}}" 2>/dev/null || true); \
	  if [ -z "$$MP" ]; then echo "❌ Could not locate mountpoint for $$VOL"; exit 1; fi; \
	  echo "Found volume $$VOL at $$MP; running sudo chmod -R 0777 $$MP"; \
	  sudo chmod -R 0777 "$$MP"; \
	  echo "✅ Permissions updated."'
## fix-nginx-cache-perms removed: We now use tmpfs for /var/cache/nginx to avoid host chmod requirements

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
	  ENV_ABS="$(abspath $(ENV_FILE))"; \
	  if [ -f "$$ENV_ABS" ]; then echo "Sourcing env: $$ENV_ABS"; set -a; . "$$ENV_ABS"; set +a; else echo "⚠️  Env file not found at $$ENV_ABS"; fi; \
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
	@./scripts/check_migrations.sh "$(ENV_FILE)" "$(COMPOSE_FILES)"

backfill-embeddings:  ## Backfill embeddings for recipes without one (Docker)
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) exec backend sh -lc "uv run python scripts/backfill_embeddings.py"

backfill-embeddings-dry-run:  ## Show recipes that need embeddings (no changes, Docker)
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) exec backend sh -lc "uv run python scripts/backfill_embeddings.py --dry-run"

backfill-embeddings-local:  ## Backfill embeddings (direct execution, for cloud/non-Docker)
	cd apps/backend && PYTHONPATH=./src uv run python scripts/backfill_embeddings.py

backfill-embeddings-local-dry-run:  ## Show recipes needing embeddings (direct execution, for cloud/non-Docker)
	cd apps/backend && PYTHONPATH=./src uv run python scripts/backfill_embeddings.py --dry-run

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
