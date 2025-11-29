# =============================================================================
# Backend Dockerfile for PantryPilot FastAPI Application
# Based on Astral uv + FastAPI + Docker best practices
# =============================================================================

# =============================================================================
# DEVELOPMENT STAGE
# =============================================================================
FROM python:3.12-slim-bookworm AS development

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# uv environment variables for container optimization
ENV UV_SYSTEM_PYTHON=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Set working directory
WORKDIR /app

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies only (not the project itself) for better caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --group dev

# Copy the entire project
COPY . .

# Install the project in editable mode for development
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --group dev

# Create non-root user for security
RUN groupadd -r app && useradd -r -g app app
RUN chown -R app:app /app
RUN mkdir -p /home/app/.cache && chown -R app:app /home/app
USER app

# Expose development port
EXPOSE 8000

# Development command (will be overridden by docker-compose for hot reload)
CMD ["uv", "run", "fastapi", "dev", "src/main.py", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# PRODUCTION BUILDER STAGE
# =============================================================================
FROM python:3.12-slim-bookworm AS builder

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# uv environment variables for optimal production builds
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev dependencies, no editable installs)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable

# Copy the project source
COPY . .

# Install the project (not in editable mode)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# =============================================================================
# PRODUCTION STAGE
# =============================================================================
FROM python:3.12-slim-bookworm AS production

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for production runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# uv environment variables for production
ENV UV_SYSTEM_PYTHON=1

# Create non-root user
RUN groupadd -r app && useradd -r -g app -d /app app

# Set working directory
WORKDIR /app

# Copy the virtual environment from builder stage
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy application source
COPY --chown=app:app . .

# Create cache directory for uv and set permissions
RUN mkdir -p /app/.cache && chown -R app:app /app

# Make sure the virtual environment is in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Expose port (internal only, not mapped in production)
EXPOSE 8000

# Production command with gunicorn + uvicorn workers via uv (consistent toolchain; .venv now isolated by .dockerignore)
# --forwarded-allow-ips="*" enables X-Forwarded-* header processing for reverse proxies (Azure Container Apps, nginx)
# --workers=2 optimizes for Azure Container Apps 0.5 CPU allocation (2 workers = 1 per 0.25 CPU)
CMD ["uv", "run", "gunicorn", "src.main:app", \
    "--workers", "2", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--bind", "0.0.0.0:8000", \
    "--forwarded-allow-ips", "*", \
    "--worker-tmp-dir", "/dev/shm", \
    "--max-requests", "1000", \
    "--max-requests-jitter", "50", \
    "--preload", \
    "--timeout", "120", \
    "--keep-alive", "5"]
