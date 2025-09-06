# Context

## Current work focus
Update the Memory Bank using the authoritative Makefile to accurately document development workflows, Docker Compose environment selection, database lifecycle operations, and cleanup commands.

## Recent changes
- Updated tech documentation with precise Make targets and behaviors based on the Makefile:
  - Environment/Compose flows, migrations, installation, code quality, testing, convenience, database ops, and cleanup commands
  - Added quick usage examples and tool notes
  - File: [.kilocode/rules/memory-bank/tech.md](.kilocode/rules/memory-bank/tech.md)
- Created architecture summary capturing runtime topology and critical flows:
  - Env overlays: base + dev/prod compose files; .env.dev/.env.prod
  - Startup flow: docker compose up -d; DB readiness via pg_isready; Alembic migrations via uv run
  - DB lifecycle and preservation strategy, DB scripts, CI/quality flows, developer setup
  - File: [.kilocode/rules/memory-bank/architecture.md](.kilocode/rules/memory-bank/architecture.md)

## Next steps
- Keep README, Makefile, and Memory Bank aligned; consider cross-linking key tasks in README to Memory Bank sections
- Validate presence of referenced scripts and adjust docs if needed:
  - [db/backup.sh](db/backup.sh), [db/restore.sh](db/restore.sh), [db/maintenance.sh](db/maintenance.sh), [scripts/check_migrations.sh](scripts/check_migrations.sh)
- Optionally document repeatable maintenance workflows in tasks:
  - Examples: reset-db-volume, clean-deps, clean-keep-db as task entries in [.kilocode/rules/memory-bank/tasks.md](.kilocode/rules/memory-bank/tasks.md)

## Timestamp
Updated: 2025-09-06
