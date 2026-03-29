# Release 3.0.0 — 2026-03-29

**152 commits | 146 files changed | +27,919 / -4,779 lines**
Last production release: Release/2.0.3 (2026-01-28)

---

## Highlights

- **Azure ML Training Pipeline** — New training infrastructure with DAPT corpus prep, SFT/GRPO/reward scripts, persona seeding, and Azure ML integration
- **Chat Agent Improvements** — Overhauled recipe search tools (~50% token reduction), added AI-generated titles, feedback system, training data capture, and centralized model factory
- **Meal Plan UX Fixes** — Resolved crashes, improved mobile view, fixed timezone handling
- **Infrastructure** — New OpenAI Bicep module, Container App environment updates, PostgreSQL hardening
- **Dependency Overhaul** — All frontend, backend, and GitHub Actions dependencies updated to latest versions

---

## New: Azure ML Training Pipeline

Entirely new `training/` directory and `apps/backend/src/training/` module:

- DAPT corpus preparation: download, process, and upload Food.com and OpenRecipes datasets
- SFT, GRPO, and DAPT training scripts with Unsloth integration
- Reward function library with tests
- Azure ML pipeline submission and model registration scripts
- Persona definitions and synthetic user seeding for conversation generation
- Conversation generation from query templates
- Training environment config (`unsloth-env.yml`)

---

## Features

### Chat Agent Enhancements
- Centralized AI model factory with Azure OpenAI support — new `model_factory.py` (#314)
- AI-generated conversation titles with background scheduler — new `chat_title_generator.py`, `scheduler.py` (#310)
- Training data capture from conversations — new `training_capture.py` (#312, #349, #370)
- Chat feedback API and UI — new `feedback.py` endpoint, `FeedbackButtons` component (#324)
- Recipe tools rewritten with hybrid search (~446 lines changed) (#275, #357)
- Agent tool token usage optimized ~50% (#357)
- Chat token budget stabilization (#366)
- Chat history pagination returns newest first (#373)
- Tool calls/results now included in chat history (#311)

### Meal Plan & Recipes
- Meal plan page crash and mobile UX fixes (#363)
- Mobile meal plan view improvements (+76/-30 lines) (#288)
- Meal plan page simplified (-78/+65 lines)
- Timezone handling fixed — uses browser local time instead of UTC (#318)
- New `dateUtils.ts` utility module

### Infrastructure & Cloud
- New `infra/modules/openai.bicep` — dedicated OpenAI module (+91 lines)
- Container Apps: added env vars for Brave Search, Gemini API, ACS, FRONTEND_URL (+65 lines)
- PostgreSQL: added resource dependencies to avoid ServerIsBusy errors (#347)
- Bicep API version fixes: reverted to 2025-06-01, omit raiPolicyName (#374-#377)
- Azure OpenAI deployment capacity reduction for cost optimization
- Production PostgreSQL storage updated to 128GB (#241)
- Log Analytics retention set to 30 days (#239)
- SPA fallback routing for verify-email deep links (#231)

---

## Bug Fixes

### Security
- Resolve 2 high-severity CVEs: CVE-2024-23342, CVE-2026-0994 (#326)
- Reduce email verification token expiration from 24h to 1h (#245)

### Application
- Meal plan page crash and mobile UX issues (#363)
- Prevent false session expired toast for unauthenticated users (#306)
- User messages not appearing in chat history (#302)
- Draft commit after image upload to fix streaming endpoint (#300)
- Prevent logout when draft token expires in AI recipe deep links (#289)
- Truncate search_recipes results in SSE stream (#278)
- Skip title generation for conversations with insufficient messages
- Reasoning model params and markdown list rendering (#315)
- Recipe description and oven_temperature_f persistence (#235)
- Deployment token issues (#281)

---

## Build & Dependencies

### Combined Updates (2026-03-29)
- Frontend: all npm dependencies updated to latest minor/patch (#402)
- Backend: all uv dependencies upgraded, pyproject.toml lower bounds bumped (#404)
- GitHub Actions: upload-artifact v7, setup-qemu v4, setup-buildx v4, login-action v4, metadata-action v6 (#405)

### Individual Dependency Bumps
- 40+ dependabot PRs merged covering: react, vite, tailwindcss, eslint, typescript-eslint, vitest, jsdom, prettier, zustand, react-router-dom, lucide-react, msw, tar, pillow, pydantic-ai, gunicorn, aiosqlite, greenlet, pre-commit, kaggle, pyasn1, python-multipart, minimatch, rollup, and more

### Build System
- Migrate recipe enums to StrEnum for Ruff 0.15.0 compatibility
- Update eslint config for react-refresh v0.5.0 compatibility
- Dependabot: change package-ecosystem from pip to uv, add grouping (#327)
- CI pipeline runs on production PRs (#206, #212)
- Agents directory renamed from `.github/chatmodes/` to `.github/agents/`
