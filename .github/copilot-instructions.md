# PantryPilot - GitHub Copilot Instructions

PantryPilot is a full-stack AI-powered recipe recommendation system that helps families plan weekly meals and grocery lists. The application is built with a modern monorepo architecture using Docker containerization.

## Project Architecture

This is a **monorepo** with the following structure:

- `apps/backend/` - FastAPI Python backend with PostgreSQL
- `apps/frontend/` - React TypeScript frontend with Vite
- `db/` - PostgreSQL database scripts and migrations
- `nginx/` - Nginx reverse proxy configuration

## Technology Stack

### Backend (Python FastAPI)

- **Python**: 3.12+
- **FastAPI**: 0.116.1+ with standard extras
- **Uvicorn**: 0.35.0+ (ASGI server)
- **Gunicorn**: 23.0.0+ (production WSGI server)
- **Alembic**: 1.16.4+ (database migrations)
- **uv**: Latest (Python package and environment manager)
- **Ruff**: 0.12.5+ (linting and formatting)
- **mypy**: 1.14.2+ (type checking)
- **pytest**: 8.4.1+ (testing framework)

### Frontend (React TypeScript)

- **React**: 19.1.0+ (latest with new hooks and features)
- **TypeScript**: 5.8.3+ (strict mode enabled)
- **Vite**: 7.0.4+ (build tool and dev server)
- **Tailwind CSS**: 4.1.11+ (utility-first CSS framework)
- **Vitest**: 3.2.4+ (testing framework)
- **ESLint**: 9.30.1+ (linting)
- **Prettier**: 3.6.2+ (formatting)

### Infrastructure

- **PostgreSQL**: 15-alpine (database)
- **Docker**: Multi-stage builds with development and production targets
- **Docker Compose**: Environment-based configuration (dev/prod)
- **Nginx**: Reverse proxy and static file serving

## Development Workflow

### Environment Management

- Use `make` commands for all development tasks
- Environment variables managed through `.env.dev` and `.env.prod`
- Docker Compose with environment-specific overrides

### Code Quality

- **Backend**: Ruff for linting/formatting, mypy for type checking, pytest for testing
- **Frontend**: ESLint for linting, Prettier for formatting, TypeScript strict mode, Vitest for testing
- Pre-commit hooks for automated quality checks

### Database Operations

- Alembic migrations for schema changes
- Database backup/restore scripts
- Maintenance commands for optimization

## Key Patterns

### Backend Patterns

- FastAPI dependency injection system
- Pydantic models for request/response validation
- SQLAlchemy ORM with async support
- Structured logging and error handling
- API versioning (`/api/v1/`)

### Frontend Patterns

- Functional components with React hooks
- TypeScript strict mode with proper type definitions
- Custom hooks for reusable logic
- Component composition patterns
- Tailwind CSS utility classes

### Infrastructure Patterns

- Multi-stage Docker builds for optimization
- Environment-specific configurations
- Health checks for all services
- Volume management for data persistence

## Context7 Integration

When providing examples or documentation, leverage the Context7 MCP server to fetch up-to-date information from:

- **FastAPI**: Use `/tiangolo/fastapi` for official FastAPI documentation and patterns
- **React**: Use `/reactjs/react.dev` for modern React patterns and best practices
- **Python Best Practices**: Reference official Python documentation and PEP standards
- **TypeScript**: Use official TypeScript documentation for type patterns

## Code Generation Guidelines

### When working in `apps/backend/`:

- Follow FastAPI dependency injection patterns
- Use uv for package management (`uv add`, `uv sync`)
- Implement proper type hints with Pydantic models
- Structure modules according to FastAPI best practices
- Use async/await patterns for database operations

### When working in `apps/frontend/`:

- Use React 19+ features and modern hook patterns
- Implement TypeScript strict mode compliance
- Follow Tailwind CSS utility-first approach
- Structure components with proper separation of concerns
- Use Vitest for testing with React Testing Library

### When working with Docker/Infrastructure:

- Follow multi-stage build patterns
- Implement proper health checks
- Use environment-specific configurations
- Optimize for both development and production

## Development Commands

```bash
# Project setup
make install              # Install all dependencies
make dev-setup           # Set up development environment

# Development workflow
make up                  # Start all services
make logs               # View service logs
make down               # Stop all services

# Code quality
make lint               # Run all linters
make type-check         # Run type checking
make format             # Format all code
make test               # Run all tests

# Database operations
make db-shell           # Open PostgreSQL shell
make db-backup          # Create database backup
make reset-db           # Reset development database
```

This project emphasizes developer experience, type safety, and modern best practices across the entire stack.
