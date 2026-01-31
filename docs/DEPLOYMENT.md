# Deployment & Local Development Guide

This project uses Docker Compose with environment-specific overrides and a Makefile for common workflows.

## Prerequisites

- Docker Desktop: <https://www.docker.com/products/docker-desktop/>
- uv (Python package & env manager): <https://docs.astral.sh/uv/>
- Node.js & npm: <https://nodejs.org/> and <https://docs.npmjs.com/>

These tools let you run the full stack locally and work on backend (Python) and frontend (React) code.

## Local Development (Docker Compose)

- Start services (development): `make dev` (uses `.env.dev` + `docker-compose.dev.yml`)
- Start services (production): `make prod` (alias for `ENV=prod make up`, uses `.env.prod` + `docker-compose.prod.yml`)
- View logs: `make logs`
- Stop services: `make down`

Notes:

- Backend API is exposed under `/api/v1`. Swagger UI is available at `/api/v1/docs` and Redoc at `/api/v1/redoc`.
- Database migrations run automatically during startup; see below for manual control.

## Database Migrations

- Apply migrations (current ENV): `make migrate`
- Validate Alembic migrations on a temporary DB: `make check-migrations`
- Reset development DB (destructive): see `make reset-db` targets in the Makefile.

## Code Quality & Tests (local)

You can run these from the project root via Makefile shortcuts:

- Lint all: `make lint`
- Type-check all: `make type-check`
- Tests (backend + frontend): `make test`
- Backend coverage (HTML at `apps/backend/htmlcov/index.html`): use the VS Code task "Test: Run with Coverage" or run the backend coverage command directly.

Backend-only (optional, via uv):

- Lint: `cd apps/backend && uv run ruff check .`
- Type-check: `cd apps/backend && uv run mypy -p api -p core -p crud -p dependencies -p models -p schemas`
- Tests: `cd apps/backend && uv run pytest`

Frontend-only (optional, via npm):

- Type-check: `cd apps/frontend && npm run type-check`
- Tests: `cd apps/frontend && npm test`

## Images & Runtime

- Backend image: multi-stage with `uv` and `gunicorn+uvicorn` workers
- Frontend image: Vite static build served behind Nginx
- Reverse proxy: Nginx configuration in `nginx/`

## Environment Configuration

- Set `CORS_ORIGINS` appropriately (e.g., dev `http://localhost:5173`)
- Configure database credentials in `.env.dev` and `.env.prod`

See the root `README.md` for an overview and quick-start commands, and `docs/API_DESIGN.md` for API details.

## Azure OpenAI Setup

PantryPilot supports Azure OpenAI as an alternative to Google Gemini for all AI features including chat, recipe extraction, embeddings, and context generation.

### Option 1: Bicep Deployment (Recommended)

The Bicep infrastructure includes Azure OpenAI provisioning with all required model deployments:

1. Enable Azure OpenAI in parameters:
   ```bash
   # In infra/parameters/main.dev.bicepparam or main.prod.bicepparam
   param deployAzureOpenAI = true
   ```

2. Deploy infrastructure:
   ```bash
   az deployment group create \
     --resource-group pantrypilot-rg \
     --template-file infra/main.bicep \
     --parameters infra/parameters/main.dev.bicepparam
   ```

3. Get the deployment outputs:
   ```bash
   az deployment group show \
     --resource-group pantrypilot-rg \
     --name main \
     --query properties.outputs
   ```

### Option 2: Manual Azure CLI

1. Create Azure OpenAI resource:
   ```bash
   az cognitiveservices account create \
     --name pantrypilot-openai \
     --resource-group pantrypilot-rg \
     --kind OpenAI \
     --sku S0 \
     --location eastus
   ```

2. Deploy required models:
   ```bash
   # Chat/completion model (gpt-4o-mini)
   az cognitiveservices account deployment create \
     --name pantrypilot-openai \
     --resource-group pantrypilot-rg \
     --deployment-name gpt-4o-mini \
     --model-name gpt-4o-mini \
     --model-version "2024-07-18" \
     --model-format OpenAI \
     --sku-capacity 10 \
     --sku-name Standard

   # Multimodal model for image extraction (gpt-4o)
   az cognitiveservices account deployment create \
     --name pantrypilot-openai \
     --resource-group pantrypilot-rg \
     --deployment-name gpt-4o \
     --model-name gpt-4o \
     --model-version "2024-08-06" \
     --model-format OpenAI \
     --sku-capacity 5 \
     --sku-name Standard

   # Embedding model for semantic search
   az cognitiveservices account deployment create \
     --name pantrypilot-openai \
     --resource-group pantrypilot-rg \
     --deployment-name text-embedding-3-small \
     --model-name text-embedding-3-small \
     --model-version "1" \
     --model-format OpenAI \
     --sku-capacity 50 \
     --sku-name Standard
   ```

3. Get endpoint and API key:
   ```bash
   # Endpoint
   az cognitiveservices account show \
     --name pantrypilot-openai \
     --resource-group pantrypilot-rg \
     --query properties.endpoint -o tsv

   # API Key
   az cognitiveservices account keys list \
     --name pantrypilot-openai \
     --resource-group pantrypilot-rg \
     --query key1 -o tsv
   ```

### Configure Environment

Add to your `.env.dev` or `.env.prod`:

```bash
USE_AZURE_OPENAI=true
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-10-01-preview

# Model deployments
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini              # Chat, recipe extraction, titles
AZURE_OPENAI_MULTIMODAL_DEPLOYMENT=gpt-4o        # Image-based recipe extraction
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small  # Semantic search
```

### Verify Configuration

Start the backend and check logs for:
```
INFO: Using Azure OpenAI for recipe extraction
INFO: Using Azure OpenAI for embeddings
INFO: Using Azure OpenAI for title generation
```
