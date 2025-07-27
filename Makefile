# Makefile for PantryPilot

.PHONY: help up down reset-db lint lint-backend lint-frontend type-check type-check-backend type-check-frontend format format-backend format-frontend test test-backend test-frontend test-coverage install install-backend install-frontend check ci dev-setup clean

help:
	@echo "Available targets:"
	@echo "  up                 - Start all services"
	@echo "  down               - Stop all services"
	@echo "  reset-db           - Reset and migrate the database"
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

up:
	# Start services using Docker Compose
	docker-compose up -d

down:
	# Stop services
	docker-compose down

reset-db:
	# Reset database: stop, remove volumes, and start fresh
	docker-compose down -v
	docker-compose up -d
	# TODO: Add migration commands here

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
