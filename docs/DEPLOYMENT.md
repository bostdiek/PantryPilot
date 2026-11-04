---
title: Deployment & Local Development Guide
description: Local development, Azure deployment, and infrastructure API lifecycle guidance for PantryPilot.
---

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

## Azure Infrastructure API Versions

The deployment workflows use `infra/main.bicep` directly. Keep Bicep as the
source of truth; generated ARM JSON under `infra/` is ignored by Git.

| Resource family | Management API version | Retirement addressed |
|---|---|---|
| PostgreSQL server, configurations, databases, firewall rules | `2025-08-01` (stable) | `2023-06-01-preview` retires January 30, 2027 |
| Key Vault vaults and ARM-managed secrets | `2026-02-01` (stable) | Control-plane versions before `2026-02-01` retire February 27, 2027 |

These are management API updates, not a PostgreSQL engine upgrade or a data
migration. PostgreSQL remains version 15. Resource names, database names,
permissions, firewall settings, backups and secret references are unchanged.
Key Vault RBAC remains explicitly configured rather than relying on the newer
API's default.

The separate January 31, 2027 retirement of Key Vault `2026-03-01-preview`
does not match any explicitly selected API in this repository. Container Apps
uses managed Key Vault secret references; deployment and migration scripts read
secrets through Azure CLI. Keep Azure CLI current, and check other clients
separately because management and secret-access APIs have independent versions.

### Local Compilation

Use a recent Bicep release with the target resource schemas. Compilation was
validated with Bicep `0.48.1`; older releases such as `0.39.26` report `BCP081`
for Key Vault `2026-02-01`. Upgrade rather than suppressing missing-type warnings:

```bash
az bicep upgrade
az bicep build --file infra/main.bicep
az bicep build --file infra/modules/postgresql.bicep
az bicep build --file infra/modules/keyvault.bicep
```

These commands compile locally and regenerate ignored JSON; they do not deploy
or require database credentials. Do not edit or commit the generated files.

### Before Deploying an API Update

1. Select the intended Azure subscription and use the existing environment's
   resource group and parameter file. Preserve the environment's current suffixes,
   resource names and settings.
2. Provide the required environment variables through your existing secure
   deployment process. Do not substitute validation-only credentials in a real
   deployment.
3. Run a what-if for development first:

   ```bash
   az deployment group what-if \
     --resource-group "<existing-development-resource-group>" \
     --template-file infra/main.bicep \
     --parameters infra/parameters/main.dev.bicepparam
   ```

4. Review the result for unintended replacements, deletions, permission changes
   or network changes. Stop and investigate any such changes before deployment.
5. After an approved development deployment, verify database connectivity,
   recipe reads, managed secret access and migrations. Repeat what-if with the
   existing production resource group and `main.prod.bicepparam` before an
   approved production rollout.

Local compilation alone does not confirm Azure provider acceptance or runtime
health. No live what-if or rollout is implied by these instructions.

References:

- [PostgreSQL API lifecycle](https://learn.microsoft.com/en-us/rest/api/postgresql/preview-api-lifecycle)
- [Supported PostgreSQL APIs](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/release-notes-api)
- [Key Vault API migration and retirement guidance](https://learn.microsoft.com/en-us/azure/key-vault/general/migrate-api-version)
- [Key Vault RBAC defaults](https://learn.microsoft.com/en-us/azure/key-vault/general/access-control-default)

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
LLM_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-10-01-preview

# Model deployments (Azure OpenAI deployment names)
CHAT_MODEL=gpt-4o-mini                    # Chat, recipe extraction, titles
TEXT_MODEL=gpt-4o-mini                    # Text-only generation
MULTIMODAL_MODEL=gpt-4o                   # Image-based recipe extraction
EMBEDDING_MODEL=text-embedding-3-small    # Semantic search
```

### Verify Configuration

Start the backend and check logs for:
```
INFO: Using Azure OpenAI chat model: gpt-4o-mini
INFO: Using Azure OpenAI for embeddings: text-embedding-3-small
INFO: Using Azure OpenAI text model: gpt-4o-mini
```
