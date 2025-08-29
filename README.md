# PantryPilot

[![CI](https://github.com/bryanostdiek/pantrypilot/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/bryanostdiek/pantrypilot/actions/workflows/ci.yml)
[![Coverage Status](https://codecov.io/gh/bryanostdiek/pantrypilot/branch/main/graph/badge.svg)](https://codecov.io/gh/bryanostdiek/pantrypilot)

Helps families plan the weekly meals and grocery list

> **🚧 Current Status**: This project is in early development with Docker Compose setup and basic database schema for demonstration purposes. The current database schema is **for testing and development workflow validation only**. The actual production schema for the AI-powered recipe recommendation system will be designed collaboratively based on specific requirements for ingredient analysis, recipe matching, and machine learning integration.

## Coverage

PantryPilot collects code coverage in CI for both backend (pytest + coverage.py) and frontend (Vitest). Reports are uploaded to Codecov.

- CI workflow: see `.github/workflows/ci.yml` for steps uploading `apps/backend/coverage.xml` and `apps/frontend/coverage/lcov.info`.
- Project dashboard: <https://codecov.io/gh/bryanostdiek/pantrypilot>

Local commands:

- Backend (terminal):
	- make test-coverage
	- Generates terminal summary and HTML at `apps/backend/htmlcov/index.html`
- Frontend (terminal):
	- npm run test:coverage (from `apps/frontend`)
	- Outputs lcov + HTML in `apps/frontend/coverage/`

VS Code tasks:

- Test: Run with Coverage (backend)

## Quick Start

```bash
# Start development environment
make up

# View logs
make logs

# Run database health check
make db-maintenance CMD=health

# Stop services
make down
```

## Proposed structure

```text
pantrypilot/
├── apps/
│   ├── backend/
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── api/                  # Routers, endpoints
│   │   │   ├── core/                 # Config, settings, security
│   │   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── schemas/              # Pydantic schemas
│   │   │   ├── crud/                 # Database operations/services
│   │   │   └── dependencies/         # FastAPI dependencies
│   │   ├── alembic/                  # DB migrations
│   │   │   ├── env.py                # Migration environment setup
│   │   │   └── versions/             # Auto-generated migration scripts
│   │   ├── alembic.ini               # Alembic configuration file
│   │   ├── tests/                    # Backend unit & integration tests
│   │   ├── Dockerfile
│   │   └── requirements.txt or pyproject.toml
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── components/           # UI components
│   │   │   ├── pages/routes/
│   │   │   ├── api/                  # API wrapper (fetch/axios client)
│   │   │   ├── hooks/                # Custom React hooks
│   │   │   ├── types/                # Shared TS types
│   │   │   └── App.tsx, main.tsx, etc.
│   │   ├── public/
│   │   ├── vite.config.ts
│   │   └── package.json
│   └── shared/ (optional)
│       ├── types/                    # Shared types/interfaces
│       └── utils/                    # Shared helper code
├── db/
│   ├── schema.sql or other seeds
│   └── docker-entrypoint scripts
├── docker-compose.yml
├── .env
├── Makefile or tools scripts
├── README.md
└── .gitignore
```
