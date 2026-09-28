#!/usr/bin/env bash
# Copyright (c) 2026 Microsoft Corporation. All rights reserved.
# SPDX-License-Identifier: MIT
#
# Validate Alembic ownership migrations and fresh database initialization.

set -euo pipefail

ENV_FILE="${1:-.env.dev}"
if [[ $# -ge 1 ]]; then
  shift
fi

if [[ $# -gt 0 ]]; then
  if [[ $# -eq 1 ]]; then
    read -r -a COMPOSE_ARGS <<< "$1"
  else
    COMPOSE_ARGS=("$@")
  fi
else
  COMPOSE_ARGS=(-f docker-compose.yml -f docker-compose.dev.yml)
fi

read_env_value() {
  local key="$1"
  if [[ ! -f "${ENV_FILE}" ]]; then
    return
  fi
  awk -F= -v key="${key}" '
    $1 == key {
      value = substr($0, index($0, "=") + 1)
      gsub(/^["'\'']|["'\'']$/, "", value)
      print value
      exit
    }
  ' "${ENV_FILE}"
}

POSTGRES_USER="${POSTGRES_USER:-$(read_env_value POSTGRES_USER)}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(read_env_value POSTGRES_PASSWORD)}"
POSTGRES_DB="${POSTGRES_DB:-$(read_env_value POSTGRES_DB)}"
POSTGRES_USER="${POSTGRES_USER:-pantry_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-secure_password}"
POSTGRES_DB="${POSTGRES_DB:-pantry_db}"
MIGRATION_RUNNER="${MIGRATION_RUNNER:-docker}"
LOCAL_DATABASE_HOST="${LOCAL_DATABASE_HOST:-localhost}"
LOCAL_DATABASE_PORT="${LOCAL_DATABASE_PORT:-5432}"
TMPDB="${POSTGRES_DB}_migrate_check_${RANDOM}"
TMPDEV="${POSTGRES_DB}_dev_init_check_${RANDOM}"

compose() {
  docker compose --env-file "${ENV_FILE}" "${COMPOSE_ARGS[@]}" "$@"
}

database_url() {
  local database="$1"
  local host="db"
  if [[ "${MIGRATION_RUNNER}" == "local" ]]; then
    host="${LOCAL_DATABASE_HOST}"
  fi
  local port="5432"
  if [[ "${MIGRATION_RUNNER}" == "local" ]]; then
    port="${LOCAL_DATABASE_PORT}"
  fi
  # pragma: allowlist nextline secret
  printf 'postgresql+asyncpg://%s:%s@%s:%s/%s' \
    "${POSTGRES_USER}" "${POSTGRES_PASSWORD}" "${host}" "${port}" "${database}"
}

run_alembic() {
  local database="$1"
  shift
  if [[ "${MIGRATION_RUNNER}" == "local" ]]; then
    (
      cd apps/backend
      DATABASE_URL="$(database_url "${database}")" \
        uv run alembic -c src/alembic.ini "$@"
    )
    return
  fi
  compose run --rm \
    -e DATABASE_URL="$(database_url "${database}")" \
    backend sh -lc "uv run alembic -c /app/src/alembic.ini $*"
}

psql_exec() {
  local database="$1"
  shift
  compose exec -T db \
    psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${database}" "$@"
}

create_database() {
  local database="$1"
  psql_exec "${POSTGRES_DB}" -c "CREATE DATABASE \"${database}\";" >/dev/null
}

drop_database() {
  local database="$1"
  psql_exec "${POSTGRES_DB}" \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${database}';" \
    >/dev/null || true
  psql_exec "${POSTGRES_DB}" \
    -c "DROP DATABASE IF EXISTS \"${database}\";" >/dev/null || true
}

cleanup() {
  drop_database "${TMPDB}"
  drop_database "${TMPDEV}"
  echo "Temporary migration databases removed."
}

wait_for_database() {
  local attempts=30
  until compose exec -T db \
    pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; do
    attempts=$((attempts - 1))
    if ((attempts <= 0)); then
      echo "Database did not become ready." >&2
      exit 1
    fi
    sleep 2
  done
}

stage_representative_snapshot() {
  run_alembic "${TMPDB}" upgrade 20260131_18
  psql_exec "${TMPDB}" <<'SQL'
INSERT INTO users (id, username, email, hashed_password)
VALUES
  ('10000000-0000-0000-0000-000000000001', 'owner_one', 'owner1@example.test', 'hash'),
  ('10000000-0000-0000-0000-000000000002', 'owner_two', 'owner2@example.test', 'hash');

INSERT INTO recipe_names (id, user_id, name)
VALUES
  ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'Owned Recipe'),
  ('20000000-0000-0000-0000-000000000002', NULL, 'Inferable Recipe'),
  ('20000000-0000-0000-0000-000000000003', NULL, 'Ambiguous Recipe'),
  ('20000000-0000-0000-0000-000000000004', NULL, 'Unreferenced Recipe');

INSERT INTO ingredient_names (id, user_id, ingredient_name)
VALUES
  ('30000000-0000-0000-0000-000000000001', NULL, 'Legacy Eggs'),
  ('30000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', 'Salt'),
  ('30000000-0000-0000-0000-000000000003', NULL, 'salt'),
  ('30000000-0000-0000-0000-000000000004', NULL, 'Pepper'),
  ('30000000-0000-0000-0000-000000000005', NULL, 'pepper');

INSERT INTO recipe_ingredients (id, recipe_id, ingredient_id)
VALUES
  ('40000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000002'),
  ('40000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000003'),
  ('40000000-0000-0000-0000-000000000005', '20000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000004'),
  ('40000000-0000-0000-0000-000000000006', '20000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000005');

INSERT INTO meal_history (id, user_id, recipe_id, planned_for_date)
VALUES
  ('50000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000002', '2026-09-28'),
  ('50000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000003', '2026-09-29'),
  ('50000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000003', '2026-09-30'),
  ('50000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001', '2026-10-01');
SQL
}

assert_upgraded_snapshot() {
  psql_exec "${TMPDB}" <<'SQL'
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM recipe_names WHERE user_id IS NULL) THEN
    RAISE EXCEPTION 'recipe owner null after upgrade';
  END IF;
  IF EXISTS (SELECT 1 FROM ingredient_names WHERE user_id IS NULL) THEN
    RAISE EXCEPTION 'ingredient owner null after upgrade';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM recipe_names
    WHERE id = '20000000-0000-0000-0000-000000000002'
      AND user_id = '10000000-0000-0000-0000-000000000001'
  ) THEN
    RAISE EXCEPTION 'inferable recipe owner was not assigned';
  END IF;
  IF EXISTS (
    SELECT 1 FROM recipe_names
    WHERE id IN (
      '20000000-0000-0000-0000-000000000003',
      '20000000-0000-0000-0000-000000000004'
    )
  ) THEN
    RAISE EXCEPTION 'unresolved recipes remain active';
  END IF;
  IF (SELECT COUNT(*) FROM ownership_recipe_quarantine) <> 2 THEN
    RAISE EXCEPTION 'unexpected recipe quarantine count';
  END IF;
  IF (
    SELECT COUNT(DISTINCT ri.ingredient_id)
    FROM recipe_ingredients AS ri
    WHERE ri.id IN (
      '40000000-0000-0000-0000-000000000005',
      '40000000-0000-0000-0000-000000000006'
    )
  ) <> 1 THEN
    RAISE EXCEPTION 'normalized legacy ingredients did not share one target';
  END IF;
  IF NOT EXISTS (
    SELECT 1
    FROM recipe_ingredients
    WHERE id = '40000000-0000-0000-0000-000000000003'
      AND ingredient_id = '30000000-0000-0000-0000-000000000002'
  ) THEN
    RAISE EXCEPTION 'existing owned ingredient association changed during upgrade';
  END IF;
  IF NOT EXISTS (
    SELECT 1
    FROM recipe_ingredients
    WHERE id = '40000000-0000-0000-0000-000000000004'
      AND ingredient_id = '30000000-0000-0000-0000-000000000002'
  ) THEN
    RAISE EXCEPTION 'legacy ingredient did not reuse the owned target';
  END IF;
  IF EXISTS (
    SELECT 1 FROM meal_history
    WHERE id IN (
      '50000000-0000-0000-0000-000000000002',
      '50000000-0000-0000-0000-000000000003',
      '50000000-0000-0000-0000-000000000004'
    )
      AND recipe_id IS NOT NULL
  ) THEN
    RAISE EXCEPTION 'quarantined meal links remain attached';
  END IF;
END
$$;
SQL
}

assert_downgraded_snapshot() {
  psql_exec "${TMPDB}" <<'SQL'
DO $$
BEGIN
  IF (SELECT COUNT(*) FROM recipe_names WHERE id::text LIKE '20000000-%') <> 4 THEN
    RAISE EXCEPTION 'quarantined recipes were not restored';
  END IF;
  IF (SELECT COUNT(*) FROM recipe_ingredients WHERE id::text LIKE '40000000-%') <> 6 THEN
    RAISE EXCEPTION 'recipe ingredient links were not restored';
  END IF;
  IF EXISTS (
    SELECT 1
    FROM (
      VALUES
        ('40000000-0000-0000-0000-000000000001'::uuid, '30000000-0000-0000-0000-000000000001'::uuid),
        ('40000000-0000-0000-0000-000000000002'::uuid, '30000000-0000-0000-0000-000000000001'::uuid),
        ('40000000-0000-0000-0000-000000000003'::uuid, '30000000-0000-0000-0000-000000000002'::uuid),
        ('40000000-0000-0000-0000-000000000004'::uuid, '30000000-0000-0000-0000-000000000003'::uuid),
        ('40000000-0000-0000-0000-000000000005'::uuid, '30000000-0000-0000-0000-000000000004'::uuid),
        ('40000000-0000-0000-0000-000000000006'::uuid, '30000000-0000-0000-0000-000000000005'::uuid)
    ) AS expected(association_id, ingredient_id)
    LEFT JOIN recipe_ingredients AS actual
      ON actual.id = expected.association_id
     AND actual.ingredient_id = expected.ingredient_id
    WHERE actual.id IS NULL
  ) THEN
    RAISE EXCEPTION 'recipe ingredient identities were not restored';
  END IF;
  IF EXISTS (
    SELECT 1 FROM meal_history
    WHERE id::text LIKE '50000000-%'
      AND recipe_id IS NULL
  ) THEN
    RAISE EXCEPTION 'meal links were not restored';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM ingredient_names
    WHERE id = '30000000-0000-0000-0000-000000000001'
      AND user_id IS NULL
  ) THEN
    RAISE EXCEPTION 'legacy ingredient was not restored';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'recipe_names'
      AND column_name = 'user_id'
      AND is_nullable = 'YES'
  ) THEN
    RAISE EXCEPTION 'recipe ownership column did not return to nullable';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'ingredient_names'
      AND column_name = 'user_id'
      AND is_nullable = 'YES'
  ) THEN
    RAISE EXCEPTION 'ingredient ownership column did not return to nullable';
  END IF;
END
$$;
SQL
}

validate_representative_snapshot() {
  echo "Staging representative ownership data..."
  stage_representative_snapshot
  run_alembic "${TMPDB}" upgrade head
  assert_upgraded_snapshot
  run_alembic "${TMPDB}" downgrade 20260131_18
  assert_downgraded_snapshot
}

validate_fresh_initialization() {
  echo "Running canonical development initialization..."
  psql_exec "${TMPDEV}" \
    -f /docker-entrypoint-initdb.d/01-init.sql >/dev/null
  psql_exec "${TMPDEV}" \
    -f /docker-entrypoint-initdb.d/02-schema-setup.sql >/dev/null
  run_alembic "${TMPDEV}" upgrade head
  psql_exec "${TMPDEV}" <<'SQL'
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM recipe_names WHERE user_id IS NULL) THEN
    RAISE EXCEPTION 'fresh initialization contains ownerless recipes';
  END IF;
  IF EXISTS (SELECT 1 FROM ingredient_names WHERE user_id IS NULL) THEN
    RAISE EXCEPTION 'fresh initialization contains ownerless ingredients';
  END IF;
  IF EXISTS (SELECT 1 FROM recipe_names WHERE name = 'Simple Omelette') THEN
    RAISE EXCEPTION 'ownerless demo recipe was unexpectedly initialized';
  END IF;
END
$$;
SQL
}

main() {
  echo "Checking migrations against temporary databases..."
  compose up -d db >/dev/null
  wait_for_database
  create_database "${TMPDB}"
  create_database "${TMPDEV}"
  trap cleanup EXIT

  validate_representative_snapshot
  validate_fresh_initialization
  echo "Migrations, recovery, and fresh initialization validated."
}

main "$@"
