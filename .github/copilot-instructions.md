# PantryPilot - GitHub Copilot Instructions

PantryPilot is a full-stack AI-powered recipe recommendation system that helps families plan weekly meals and grocery lists. The application is built with a modern monorepo architecture using Docker containerization.

**ALWAYS reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Project Architecture

This is a **monorepo** with the following structure:

- `apps/backend/` - FastAPI Python backend with PostgreSQL
- `apps/frontend/` - React TypeScript frontend with Vite
- `db/` - PostgreSQL database scripts and migrations
- `nginx/` - Nginx reverse proxy configuration

## Technology Stack

### Backend (Python FastAPI)

- **Python**: 3.12+ with strict type hints
- **FastAPI**: 0.116.1+ with dependency injection and automatic validation
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

## Prerequisites

Install these tools in this order:

1. **Docker Desktop**: <https://www.docker.com/products/docker-desktop/>
2. **uv (Python package manager)**: Install with `pip install uv`
3. **Node.js & npm**: <https://nodejs.org/> (version 20+)

Verify installations:
```bash
docker --version          # Should be 20.0+
docker compose version     # Should be v2.0+
uv --version              # Should be 0.8.0+
node --version            # Should be v20.0+
npm --version             # Should be 10.0+
```

## Environment Setup

**CRITICAL**: Create environment files before running any services:

```bash
# Copy and customize environment files
cp .env.example .env.dev
cp .env.example .env.prod

# Edit .env.dev with development settings (required):
# - Change POSTGRES_PASSWORD to a secure development password
# - Set CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
# - Set VITE_API_URL=http://localhost:8000
# - Set SECRET_KEY to a development key
```

## Package Proxy and Supply-Chain Quarantine

**CRITICAL**: The maintainer's development machine installs packages only through a corporate proxy. The proxy holds each new release in quarantine for several days (up to about two weeks) before serving it. Direct access to `registry.npmjs.org` and `pypi.org` is blocked. Read this section before you install dependencies, change a lockfile, or diagnose an install failure.

### How the machine is configured

The proxy is set in user-level config, not in the repository:

- **npm**: `~/.npmrc` sets `registry=https://packagefeedproxy.microsoft.io/npm/`
- **uv**: `~/.config/uv/uv.toml` sets the default index to `https://packagefeedproxy.microsoft.io/pypi/simple`
- **Node.js**: the default `node` on `PATH` can be older than v20. Use nvm for Node 20+ before running npm or frontend tooling, for example `export PATH=~/.nvm/versions/node/v24.15.0/bin:$PATH`.

### Rules

- Never bypass the proxy. Don't pass `--registry=https://registry.npmjs.org/`, don't switch indexes, and don't turn off the quarantine. When a locked version isn't available yet, pin to the newest version the proxy serves.
- A version that is still in quarantine fails with an npm `E404` such as `Cannot find the file <pkg>-<version>.tgz ... in feed 'npm-public'`, or with a uv resolution error. CI can still pass in this state, because GitHub runners reach the public registries.
- Dependabot and upstream merges often bump packages to releases that are too new for the proxy. Check lockfile changes before assuming a local install works.
- Run a real `npm ci` in every checkout and git worktree. Don't symlink or reuse `node_modules` from another checkout. Version drift causes misleading type and test failures.

### Frontend (npm) workflow

1. List every locked version the proxy can't serve, in one pass:

   ```bash
   node scripts/check_npm_lock_availability.mjs   # defaults: apps/frontend/package-lock.json and `npm config get registry`
   ```

2. For each unavailable package, find the newest version the proxy serves (`npm view <pkg> versions --json` or `npm view <pkg> dist-tags`). Pin to it in `apps/frontend`, for example `npm install --save-dev --ignore-scripts <pkg>@^<version>`. For transitive packages, pin the direct dependency that pulls them in.
3. Keep every `resolved` URL in `package-lock.json` on `https://registry.npmjs.org/`. With its default `replace-registry-host=npmjs` setting, npm maps those URLs to the configured proxy locally, and CI and Docker use them unchanged. If npm writes a `packagefeedproxy.microsoft.io` or `ms-feed-*.pkgs.visualstudio.com` URL for an entry you changed, rewrite it to the matching `registry.npmjs.org` URL. The integrity hash stays the same.
4. Don't let npm prune the optional `node_modules/@emnapi/core` and `node_modules/@emnapi/runtime` lockfile entries. Multi-architecture Docker `npm ci` builds need them. If they disappear, restore them from the previous lockfile.
5. Check that `git diff apps/frontend/package-lock.json` is minimal. Then run a clean `rm -rf node_modules && npm ci`, followed by `npm run type-check`, `npm run lint`, and `npx vitest run`.

### Backend (uv) workflow

- `apps/backend/uv.lock` is locked against the proxy index URL (`source = { registry = "https://packagefeedproxy.microsoft.io/pypi/simple" }`). Keep it that way: CI and Docker builds can reach that index, and `uv sync --locked` fails locally when the lockfile's index doesn't match the configured one.
- If a required version is still in quarantine, lower the floor in `apps/backend/pyproject.toml` to the newest version the proxy serves. Prefer `>=` over `==` pins, so the constraint doesn't outlast the quarantine. Then run `uv lock` and verify with `uv sync --locked`.

## Working Effectively

### Bootstrap, Build, and Test the Repository

**NEVER CANCEL long-running commands. Set timeouts to 10+ minutes minimum.**

```bash
# 1. Install all dependencies (takes ~30 seconds)
make install

# 2. Run code quality checks (takes ~20 seconds total)
make lint          # Backend Ruff + Frontend ESLint: ~5 seconds
make type-check    # Backend mypy + Frontend tsc: ~17 seconds

# 3. Run all tests (takes ~15 seconds total)
make test          # Backend pytest + Frontend Vitest: ~12 seconds

# 4. Run tests with coverage (takes ~15 seconds total)
make test-coverage # Backend coverage report + HTML output: ~8 seconds
```

### Docker Development Workflow

**NOTE**: Docker builds may have SSL certificate issues in restricted network environments. Use local development workflow instead if Docker builds fail.

```bash
# Start development environment (NEVER CANCEL - can take 10+ minutes)
make dev           # Builds and starts all services with hot reload
# TIMEOUT: Set to 15+ minutes for initial build, 2+ minutes for subsequent starts

# View logs (for monitoring and debugging)
make logs

# Stop services
make down
```

### Local Development Workflow (Alternative)

If Docker builds fail due to network restrictions, use local development:

```bash
# 1. Install dependencies
make install

# 2. Start backend server (in separate terminal)
cd apps/backend
PYTHONPATH=./src uv run fastapi dev src/main.py --host 0.0.0.0 --port 8000

# 3. Start frontend server (in separate terminal)
cd apps/frontend
npm run dev

# Backend will be available at http://localhost:8000
# Frontend will be available at http://localhost:5173
# API docs at http://localhost:8000/api/v1/docs
```

### Database Operations

```bash
# Apply migrations (after DB is running)
make migrate

# Database maintenance
make db-maintenance CMD=stats    # View database statistics
make db-maintenance CMD=health   # Check database health

# Database backup/restore
make db-backup                   # Create backup
make db-restore FILE=backup.sql  # Restore from backup

# Open database shell
make db-shell
```

## Validation and Testing

**ALWAYS run complete validation after making changes:**

```bash
# 1. Code quality validation (takes ~20 seconds)
make check         # Runs lint + type-check + migration checks

# 2. Run full test suite (takes ~15 seconds)
make test

# 3. Run CI pipeline locally (takes ~45 seconds total)
make ci            # Runs install + check + test (like GitHub CI)
```

### Manual Validation Scenarios

**CRITICAL**: Always test actual functionality after making changes:

1. **Backend API Testing**:
   ```bash
   curl http://localhost:8000/api/v1/health    # Should return healthy status
   curl http://localhost:8000/api/v1/docs      # Should return Swagger UI HTML
   curl http://localhost:8000/api/v1/recipes   # Should return recipes list
   ```

2. **Frontend Application Testing**:
   - Visit http://localhost:5173 in browser
   - Navigate between pages (Home, Recipes, Meal Plan)
   - Test recipe creation form functionality
   - Test meal planning interface

3. **Full Stack Integration**:
   - Create a new recipe via frontend
   - View recipe list and details
   - Add recipe to meal plan
   - Verify data persistence

## Timing Expectations and Timeouts

**NEVER CANCEL these operations - use these timeout values:**

- **Dependency Installation**: 30 seconds (set timeout to 2+ minutes)
- **Linting**: 5 seconds (set timeout to 30+ seconds)
- **Type Checking**: 17 seconds (set timeout to 1+ minute)
- **Tests**: 12 seconds (set timeout to 30+ seconds)
- **Frontend Build**: 8 seconds (set timeout to 1+ minute)
- **Docker Initial Build**: 10-15 minutes (set timeout to 20+ minutes)
- **Docker Subsequent Starts**: 2 minutes (set timeout to 5+ minutes)

## Common Tasks and Commands

### Code Quality (run before committing)

```bash
# Format all code
make format                    # Backend Ruff + Frontend Prettier

# Individual component linting
make lint-backend             # Ruff check
make lint-frontend            # ESLint
make type-check-backend       # mypy with MYPYPATH=src
make type-check-frontend      # TypeScript compiler
```

### Testing

```bash
# Run specific test suites
make test-backend             # Python pytest
make test-frontend            # Vitest
make test-coverage            # Backend with HTML coverage report

# Run tests with specific options
cd apps/backend && uv run pytest -v                    # Verbose backend tests
cd apps/frontend && npm run test:ui                    # Frontend tests with UI
cd apps/frontend && npm run test:coverage              # Frontend coverage
```

### Build and Development

```bash
# Frontend build for production
cd apps/frontend && npm run build        # Takes ~8 seconds

# Start individual services locally
cd apps/frontend && npm run dev          # Starts on port 5173

# Preview production build
cd apps/frontend && npm run preview
```

### Database and Migration Management

```bash
# Migration operations
make check-migrations         # Validate migrations without applying
make migrate                  # Apply pending migrations
cd apps/backend && uv run alembic revision --autogenerate -m "Description"  # Create new migration

# Database maintenance
make db-maintenance CMD=analyze          # Analyze all tables
make db-maintenance CMD=vacuum           # Vacuum database
make db-maintenance CMD=stats            # Show database statistics
make db-maintenance CMD=slow-queries     # Show slow queries
```

### Cleanup and Troubleshooting

```bash
# Fix dependency issues
make clean-deps               # Remove and rebuild dependency volumes

# Complete rebuild
make clean-build              # Remove all build caches and rebuild

# Reset database
make reset-db                 # WARNING: Destroys all data
make reset-db-volume          # Reset only database volume

# Complete cleanup
make clean-all                # Remove all Docker resources (safe - PantryPilot only)
```

## Project Structure Navigation

### Key Directories

- **Backend Source**: `apps/backend/src/`
  - `api/` - FastAPI routers and endpoints
  - `core/` - Configuration and settings
  - `models/` - SQLAlchemy ORM models
  - `schemas/` - Pydantic request/response schemas
  - `crud/` - Database operations
  - `dependencies/` - FastAPI dependencies

- **Frontend Source**: `apps/frontend/src/`
  - `components/` - Reusable UI components
  - `pages/` - Page components and routes
  - `api/` - API client and endpoint wrappers
  - `hooks/` - Custom React hooks
  - `stores/` - Zustand state management
  - `types/` - TypeScript type definitions

- **Database**: `db/`
  - `init/` - Database initialization scripts
  - Schema setup and sample data

### Important Files

- **Configuration**:
  - `apps/backend/pyproject.toml` - Python dependencies and tools
  - `apps/frontend/package.json` - Node.js dependencies and scripts
  - `apps/backend/alembic.ini` - Database migration configuration

- **Build and Deploy**:
  - `docker-compose.yml` - Base Docker services
  - `docker-compose.dev.yml` - Development overrides
  - `docker-compose.prod.yml` - Production overrides
  - `Makefile` - All development commands

## API Design and Usage

- **API Base URL**: `http://localhost:8000/api/v1`
- **Documentation**: Available at `/api/v1/docs` (Swagger UI) and `/api/v1/redoc`
- **Health Check**: `/api/v1/health`
- **Authentication**: JWT-based (when implemented)

### Key API Endpoints

- `GET /api/v1/health` - Health check
- `GET /api/v1/recipes` - List recipes
- `POST /api/v1/recipes` - Create recipe
- `GET /api/v1/mealplans` - Get meal plans
- `POST /api/v1/mealplans` - Create/update meal plan

## Development Workflow Best Practices

1. **Always run validation before committing**:
   ```bash
   make lint && make type-check && make test
   ```

2. **Use environment-specific commands**:
   ```bash
   make dev              # Development with hot reload
   ENV=prod make up      # Production mode
   ```

3. **Monitor logs during development**:
   ```bash
   make logs             # All services
   make logs | grep backend    # Backend only
   ```

4. **Test database operations**:
   ```bash
   make db-maintenance CMD=health    # Verify DB health
   make db-shell                     # Interactive SQL
   ```

## Troubleshooting

### Common Issues and Solutions

1. **Docker build fails with SSL certificate errors**:
   - Use local development workflow instead
   - Network restrictions may prevent Docker builds

2. **Module import errors in backend**:
   - Ensure PYTHONPATH includes src directory
   - Use: `PYTHONPATH=./src uv run fastapi dev src/main.py`

3. **Frontend dependency issues**:
   - Run `make clean-deps` to rebuild node_modules
   - Ensure Node.js version is 20+
   - `npm ci` fails with `E404 ... in feed 'npm-public'`: the locked version is still in the proxy's quarantine. Follow [Package Proxy and Supply-Chain Quarantine](#package-proxy-and-supply-chain-quarantine).

4. **Database connection errors**:
   - Check if database is running: `make db-maintenance CMD=health`
   - Verify environment variables in `.env.dev`

5. **Port conflicts**:
   - Backend uses port 8000
   - Frontend uses port 5173
   - Database uses port 5432 (when exposed)

### Performance Notes

- Initial Docker builds can take 10-15 minutes
- Subsequent starts should be under 2 minutes
- Local development starts in under 30 seconds
- Test suites complete in under 15 seconds
- Frontend builds complete in under 10 seconds

## Environment Variables

### Required Variables (in .env.dev and .env.prod)

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` - Database credentials
- `SECRET_KEY` - JWT signing secret
- `CORS_ORIGINS` - Allowed frontend origins
- `VITE_API_URL` - Frontend API endpoint URL

### Development vs Production

- **Development**: Uses `http://localhost` origins, debug logging
- **Production**: Uses HTTPS origins, production logging, secure secrets

---

**Remember**: Always validate changes with both automated tests and manual testing. The application should work end-to-end before considering changes complete.
