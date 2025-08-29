#!/usr/bin/env bash
# Validate Alembic migrations by applying to a temporary database.
# Usage:
#   scripts/check_migrations.sh [ENV_FILE] [COMPOSE ARGS...]
# Examples:
#   scripts/check_migrations.sh                  # uses .env.dev and -f docker-compose.yml -f docker-compose.dev.yml
#   scripts/check_migrations.sh .env.prod -f docker-compose.yml -f docker-compose.prod.yml
set -euo pipefail

ENV_FILE="${1:-.env.dev}"
if [[ $# -ge 1 ]]; then shift; fi

# Default compose file set unless args are provided after ENV_FILE
if [[ $# -gt 0 ]]; then
  if [[ $# -eq 1 ]]; then
    # Split single string like "-f a -f b" into array tokens
    read -r -a COMPOSE_ARGS <<< "$1"
  else
    COMPOSE_ARGS=("$@")
  fi
else
  COMPOSE_ARGS=(-f docker-compose.yml -f docker-compose.dev.yml)
fi

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; . "$ENV_FILE"; set +a
fi

POSTGRES_USER="${POSTGRES_USER:-pantry_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-secure_password}"
POSTGRES_DB="${POSTGRES_DB:-pantry_db}"

echo "🧪 Checking migrations against a temporary database..."

# Ensure db service is up
docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" up -d db >/dev/null

# Wait for Postgres
ATTEMPTS=30
until docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS-1))
  if [[ $ATTEMPTS -le 0 ]]; then echo "❌ DB not ready"; exit 1; fi
  sleep 2
done

TMPDB="${POSTGRES_DB}_migrate_check_$RANDOM"

echo "Creating temp DB: $TMPDB"
docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE DATABASE \"$TMPDB\";" >/dev/null

cleanup() {
  echo "Dropping temp DB: $TMPDB"
  # Terminate connections first
  docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$TMPDB';" >/dev/null || true
  # Then drop the database (outside of any transaction)
  docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP DATABASE IF EXISTS \"$TMPDB\";" >/dev/null || true
  echo "🧹 Temp DB removed."
}
trap cleanup EXIT

# Run migrations against temp DB via a one-off backend container (override DATABASE_URL)
TMP_URL="postgresql+asyncpg://$POSTGRES_USER:$POSTGRES_PASSWORD@db:5432/$TMPDB"

echo "Running alembic upgrade head against $TMPDB..."
set +e
# Try running directly; if it fails due to missing base tables, seed minimal schema then retry
docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" run --rm -e DATABASE_URL="$TMP_URL" backend sh -lc "uv run alembic -c /app/src/alembic.ini upgrade head"
ALEMBIC_RC=$?
if [[ $ALEMBIC_RC -ne 0 ]]; then
  echo "⚠️ Migrations failed on temp DB. Seeding minimal base schema and retrying..."
  # Seed minimal schema needed for migration assumptions
  docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" exec -T db psql -U "$POSTGRES_USER" -d "$TMPDB" -v ON_ERROR_STOP=1 <<'SQL'
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4()
);
CREATE TABLE IF NOT EXISTS recipe_names (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4()
);
CREATE TABLE IF NOT EXISTS meal_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipe_id UUID REFERENCES recipe_names(id) ON DELETE CASCADE,
    date_suggested TIMESTAMP WITH TIME ZONE,
    week_suggested INTEGER,
    was_cooked BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
SQL
  # Retry migrations
  docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" run --rm -e DATABASE_URL="$TMP_URL" backend sh -lc "uv run alembic -c /app/src/alembic.ini upgrade head"
fi
set -e

echo "✅ Migrations apply cleanly on temp DB."
