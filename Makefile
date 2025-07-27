# Makefile for PantryPilot

.PHONY: help validate-env up up-dev up-prod down down-dev down-prod logs reset-db reset-db-dev reset-db-prod lint lint-backend lint-frontend type-check type-check-backend type-check-frontend format format-backend format-frontend test test-backend test-frontend test-coverage install install-backend install-frontend check ci dev-setup clean

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
	@echo ""
	@echo "Development:"
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
	@echo "Usage Examples:"
	@echo "  make up              # Start in development mode"
	@echo "  make ENV=prod up     # Start in production mode"
	@echo "  make logs            # View development logs"
	@echo "  make ENV=prod logs   # View production logs"

# Environment and Docker Compose targets
validate-env:
	# Validate environment configuration
	python scripts/validate-env.py

up: validate-env
	# Start services using Docker Compose (ENV=$(ENV))
	@echo "🚀 Starting PantryPilot in $(ENV) mode..."
	docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES) up -d
	@echo "✅ Services started! Check 'make logs' for output."

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
	cd apps/backend && uv run mypy src

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
check: lint type-check
	# Run all code quality checks

ci: install check test
	# Run full CI pipeline locally

dev-setup: install
	# Set up development environment
	cd apps/backend && uv run pre-commit install

clean:
	# Clean build artifacts and caches
	cd apps/backend && rm -rf .pytest_cache __pycache__ .coverage htmlcov .mypy_cache .ruff_cache
	cd apps/frontend && rm -rf node_modules/.cache dist coverage
