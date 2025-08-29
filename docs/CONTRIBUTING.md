# Contributing Guide

Thank you for considering contributing to this project! Here are some guidelines to help you get started.

## Local Development

Prerequisites:

- Docker Desktop: <https://www.docker.com/products/docker-desktop/>
- uv (Python package & env manager): <https://docs.astral.sh/uv/>
- Node.js & npm: <https://nodejs.org/> and <https://docs.npmjs.com/>

Common commands (from repo root):

- Start services (dev): `make dev`
- Start services (prod): `make prod`
- Logs: `make logs`
- Stop: `make down`
- Lint: `make lint`
- Type-check: `make type-check`
- Tests: `make test`

Backend-only (uv): `cd apps/backend && uv run pytest` | `uv run ruff check .` | `uv run mypy -p api -p core -p crud -p dependencies -p models -p schemas`

Frontend-only (npm): `cd apps/frontend && npm run type-check` | `npm test`

## Getting Started

- Fork the repository
- Clone your fork: `git clone https://github.com/your-username/PantryPilot.git`
- Create a new branch: `git checkout -b feature/your-feature`

## Making Changes

- Make your changes and commit them: `git commit -m "Add some feature"`
- Push to your branch: `git push origin feature/your-feature`

## Submitting a Pull Request

- Go to the original repository and create a pull request.
- Provide a clear description of your changes and why they are necessary.

## Code of Conduct

Please adhere to the project's code of conduct in all interactions.
