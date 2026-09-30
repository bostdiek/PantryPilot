# PantryPilot

[![CI](https://github.com/bostdiek/PantryPilot/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/bostdiek/PantryPilot/actions/workflows/ci.yml)
[![Coverage Status](https://codecov.io/gh/bostdiek/pantrypilot/branch/main/graph/badge.svg)](https://codecov.io/gh/bostdiek/pantrypilot)

Helps families plan the weekly meals and grocery list

> **🚧 Current Status**: This project is in early development with Docker Compose setup and basic database schema for demonstration purposes. The current database schema is **for testing and development workflow validation only**. The actual production schema for the AI-powered recipe recommendation system will be designed collaboratively based on specific requirements for ingredient analysis, recipe matching, and machine learning integration.

## Coverage

PantryPilot collects code coverage in CI for both backend (pytest + coverage.py) and frontend (Vitest). Reports are uploaded to Codecov.

Note: The exact CI check names shown in GitHub PRs may be used as required status checks in branch rulesets.

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

## Tech Stack

- Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic, uv
- Database: PostgreSQL
- Frontend: React, Vite, TypeScript, Tailwind CSS
- Tooling: Ruff, mypy, pytest, Vitest, Docker Compose, Nginx

## Quick Start

```bash
# Start development environment
make dev

# View logs
make logs

# Run database health check
make db-maintenance CMD=health

# Stop services
make down
```

## Development workflow

- Monorepo structure (backend FastAPI, frontend React/Vite)
- Use `make` targets for common tasks
	- make dev, make prod
	- make test, make lint, make type-check, make migrate
- Folder structure documented below

API versioning strategy: path-based under `/api/v1`. Swagger UI available at `/api/v1/docs`.

### Releases and production promotion

Release Please tracks one **application-wide** semantic version for the monorepo. Its
manifest starts at `0.1.0`, and it considers commits after the bootstrap commit in
`release-please-config.json`. The versions in the backend and frontend package
metadata are separate and are not updated by this release process.

1. For PRs into `main`, use a Conventional Commit title with a type and scope
   listed in `.github/instructions/commit-message.instructions.md`, such as
   `fix(application): correct recipe search`. Add `!` before `:` or a
   `BREAKING CHANGE:` footer to the **squash commit** for an incompatible change.
   Changing unit tests alone is not a breaking change. CI checks PR titles; when
   squashing, keep that title in the resulting commit.
2. On a push to `main`, Release Please proposes a release PR from conventional
   commits. Review and merge it to create the `vMAJOR.MINOR.PATCH` GitHub release
   and tag. The release PR uses the generated `chore(main): release ...` title,
   which CI also accepts. Version tags mark releases on `main`, not deployments.
3. After the release is ready for production, open a PR from **`main` into
   `production`**, titled `chore(application): promote main to production`.
   Select GitHub's **Create a merge commit** (not Squash and merge or Rebase and
   merge) so subsequent promotion PRs retain their ancestry. The existing
   branch-push workflows continue to deploy dev and prod.

Repository setup is required: create a `RELEASE_PLEASE_TOKEN` Actions secret
using a fine-grained PAT with Contents, Pull requests, and Issues read/write
permissions for this repository. A separate token is needed because release
PRs created with the default `GITHUB_TOKEN` do not trigger PR checks. Allow
Actions to create pull requests in repository Actions settings. In branch
protection/rulesets, require the **Release Policy**
and existing CI checks on `main` and `production`, require PRs, allow squash
merges into `main`, and use merge commits for promotions into `production`.
The PR title check cannot itself control which merge button is clicked; restrict
merge methods in repository settings where possible. Do not promote until the
release PR and CI have succeeded.

Production currently pulls the moving `:prod` backend image tag, so a release
tag alone does not guarantee an immutable production artifact or rollback.

## API Endpoints

### User Registration

Register a new user account with the registration endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser123",
    "email": "newuser123@example.com",
    "password": "averylongsecurepw",
    "first_name": "New",
    "last_name": "User"
  }'
```

Expected 201 response:
```json
{ "access_token": "...", "token_type": "bearer" }
```

Database migrations: Alembic configured; run `make migrate` or applied on `make up` after DB is healthy.

Frontend/backed commands:

- Backend: `make test-backend`, `make lint-backend`, `make type-check-backend`
- Frontend: `make test-frontend`, `make lint-frontend`, `make type-check-frontend`

Environment variables

- CORS_ORIGINS: comma-separated origins (dev defaults to `http://localhost:5173`)
- Database vars: see `.env.dev` and `.env.prod`
- **SECRET_KEY**: Required for JWT token signing. Generate a secure development key:
  ```bash
  # Generate a development SECRET_KEY (do not commit real secrets)
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
  Add the generated key to your `.env.dev` file:
  ```
  SECRET_KEY=<paste_generated_value>
  ```

## Security Features

PantryPilot includes baseline security configurations for small private deployments:

### CORS Configuration
- Restricts origins to configured frontend URLs
- Prevents wildcard origins when credentials are enabled
- Properly handles preflight requests
- Configurable via `CORS_ORIGINS` environment variable

### Security Headers (Nginx)
- **Content Security Policy**: Prevents XSS attacks and restricts resource loading
- **HSTS**: Forces HTTPS connections when enabled
- **X-Content-Type-Options**: Prevents MIME sniffing attacks
- **Referrer-Policy**: Controls referrer information disclosure
- **Frame-ancestors**: Prevents clickjacking attacks

### HTTPS Support
PantryPilot supports multiple HTTPS termination options:

```bash
# Check current HTTPS status
./scripts/https-setup.sh status

# Enable HTTPS (requires certificates)
./scripts/https-setup.sh enable

# Disable HTTPS
./scripts/https-setup.sh disable
```

For detailed HTTPS setup instructions, see `docs/HTTPS_SETUP.md`.

### Additional Security Measures
- Gzip disabled for sensitive API endpoints (BREACH attack mitigation)
- Proper credential handling in CORS
- Secure session management
- Input validation via Pydantic schemas

### Architecture Decisions
Security architecture and release planning are documented in Architecture Decision Records (ADRs):
- [ADR-001: Security Headers and CORS Configuration Baseline](docs/adr/ADR-001-security-headers-and-cors-baseline.md) - Complete security implementation with release plan
- [ADR Directory](docs/adr/README.md) - All architectural decisions

See `docs/API_DESIGN.md` and `docs/DEPLOYMENT.md` for more details. Contribution guidelines in `docs/CONTRIBUTING.md`.

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
