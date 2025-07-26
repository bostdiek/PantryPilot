# Makefile for PantryPilot

.PHONY: help up down reset-db lint test

help:
	@echo "Available targets:"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  reset-db  - Reset and migrate the database"
	@echo "  lint      - Run linters"
	@echo "  test      - Run tests"

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
	# Run linters (placeholder)
	@echo "Linting not configured yet"

test:
	# Run tests (placeholder)
	@echo "Testing not configured yet"
