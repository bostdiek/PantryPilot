# Makefile for PantryPilot

.PHONY: help up down reset-db lint test test-backend test-coverage setup-dev

help:
	@echo "Available targets:"
	@echo "  up            - Start all services"
	@echo "  down          - Stop all services"
	@echo "  reset-db      - Reset and migrate the database"
	@echo "  lint          - Run linters"
	@echo "  test          - Run all tests"
	@echo "  test-backend  - Run backend tests"
	@echo "  test-coverage - Run backend tests with coverage report"
	@echo "  setup-dev     - Set up development environment"

setup-dev:
	# Setup the development environment with uv
	cd apps/backend && uv venv && uv pip install -e . && uv pip install pytest pytest-cov httpx pre-commit ruff

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

lint:
	# Run linters
	cd apps/backend && source .venv/bin/activate && python -m ruff check .

test: test-backend

test-backend:
	# Run backend tests
	cd apps/backend && source .venv/bin/activate && python -m pytest

test-coverage:
	# Run backend tests with coverage
	cd apps/backend && source .venv/bin/activate && python -m pytest --cov=src --cov-report=term --cov-report=html
