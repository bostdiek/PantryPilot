#!/bin/bash
# =============================================================================
# PantryPilot - Migrate Data to Azure PostgreSQL
# =============================================================================
# This script exports data from a source PostgreSQL database and imports it
# into Azure PostgreSQL Flexible Server.
#
# Supports multiple sources:
#   - Local Docker container (dev environment)
#   - Remote Raspberry Pi (prod environment)
#   - Any PostgreSQL server with connection details
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# Default values
SOURCE_TYPE=""
TARGET_ENV="dev"
EXPORT_FILE=""
SKIP_EXPORT=false
SKIP_IMPORT=false
DRY_RUN=false
INCLUDE_SCHEMA=false

# Source connection defaults
SRC_HOST=""
SRC_PORT="5432"
SRC_USER=""
SRC_PASSWORD=""
SRC_DATABASE=""

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Migrate data from a PostgreSQL source to Azure PostgreSQL.

SOURCE OPTIONS (choose one):
  --docker              Use local Docker container (pantrypilot-dev-db-1)
  --pi                  Use Raspberry Pi production database
  --custom              Use custom connection (requires --src-* options)

SOURCE CONNECTION (for --custom or --pi override):
  --src-host HOST       Source database host
  --src-port PORT       Source database port [default: 5432]
  --src-user USER       Source database user
  --src-password PASS   Source database password
  --src-database DB     Source database name

TARGET OPTIONS:
  -e, --env ENV         Target Azure environment (dev|prod) [default: dev]

OPERATION OPTIONS:
  --export-only         Only export data, don't import to Azure
  --import-only FILE    Only import from existing file, skip export
  --include-schema      Include schema in export (for empty target DB)
  --dry-run             Show what would be done without executing

GENERAL:
  -h, --help            Show this help message

EXAMPLES:
  # Migrate from local Docker to Azure dev
  $0 --docker -e dev

  # Migrate from Raspberry Pi to Azure dev (for testing)
  $0 --pi -e dev

  # Migrate from Raspberry Pi to Azure prod
  $0 --pi -e prod

  # Export only (creates backup file)
  $0 --docker --export-only

  # Import existing backup to Azure
  $0 --import-only backups/pantrypilot_export_20251129.sql -e dev

  # Custom source
  $0 --custom --src-host 192.168.1.100 --src-user myuser --src-password mypass --src-database pantrypilot -e dev

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --docker)
                SOURCE_TYPE="docker"
                shift
                ;;
            --pi)
                SOURCE_TYPE="pi"
                shift
                ;;
            --custom)
                SOURCE_TYPE="custom"
                shift
                ;;
            --src-host)
                SRC_HOST="$2"
                shift 2
                ;;
            --src-port)
                SRC_PORT="$2"
                shift 2
                ;;
            --src-user)
                SRC_USER="$2"
                shift 2
                ;;
            --src-password)
                SRC_PASSWORD="$2"
                shift 2
                ;;
            --src-database)
                SRC_DATABASE="$2"
                shift 2
                ;;
            -e|--env)
                TARGET_ENV="$2"
                shift 2
                ;;
            --export-only)
                SKIP_IMPORT=true
                shift
                ;;
            --import-only)
                SKIP_EXPORT=true
                EXPORT_FILE="$2"
                shift 2
                ;;
            --include-schema)
                INCLUDE_SCHEMA=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Validate arguments
validate_args() {
    if [[ "$SKIP_EXPORT" == "false" && -z "$SOURCE_TYPE" ]]; then
        log_error "Source type is required. Use --docker, --pi, or --custom"
        show_usage
        exit 1
    fi

    if [[ "$SKIP_EXPORT" == "true" && ! -f "$EXPORT_FILE" ]]; then
        log_error "Import file not found: $EXPORT_FILE"
        exit 1
    fi

    if [[ "$TARGET_ENV" != "dev" && "$TARGET_ENV" != "prod" ]]; then
        log_error "Invalid target environment: $TARGET_ENV (expected: dev or prod)"
        exit 1
    fi
}

# Configure source based on type
configure_source() {
    case $SOURCE_TYPE in
        docker)
            log_info "Configuring Docker source..."
            # Read from .env.dev file
            if [[ -f "$PROJECT_ROOT/.env.dev" ]]; then
                source <(grep -E "^POSTGRES_" "$PROJECT_ROOT/.env.dev" | sed 's/\${[^}]*}//g')
            fi
            SRC_USER="${POSTGRES_USER:-pantrypilot_dev}"
            SRC_PASSWORD="${POSTGRES_PASSWORD:-dev_password_123}"
            SRC_DATABASE="${POSTGRES_DB:-pantrypilot_dev}"
            SRC_HOST="localhost"
            SRC_PORT="5432"
            ;;
        pi)
            log_info "Configuring Raspberry Pi source..."
            # Default Pi production settings - can be overridden with --src-* flags
            SRC_HOST="${SRC_HOST:-raspberrypi.local}"
            SRC_PORT="${SRC_PORT:-5432}"
            SRC_USER="${SRC_USER:-pantrypilot}"
            SRC_DATABASE="${SRC_DATABASE:-pantrypilot}"

            if [[ -z "$SRC_PASSWORD" ]]; then
                log_warn "No password provided for Pi. You'll be prompted."
                read -sp "Enter PostgreSQL password for ${SRC_USER}@${SRC_HOST}: " SRC_PASSWORD
                echo
            fi
            ;;
        custom)
            if [[ -z "$SRC_HOST" || -z "$SRC_USER" || -z "$SRC_DATABASE" ]]; then
                log_error "Custom source requires --src-host, --src-user, and --src-database"
                exit 1
            fi
            if [[ -z "$SRC_PASSWORD" ]]; then
                read -sp "Enter PostgreSQL password for ${SRC_USER}@${SRC_HOST}: " SRC_PASSWORD
                echo
            fi
            ;;
    esac

    log_info "Source: ${SRC_USER}@${SRC_HOST}:${SRC_PORT}/${SRC_DATABASE}"
}

# Get Azure connection string from Key Vault
get_azure_connection() {
    # Key Vault naming follows pattern from Bicep: ppkv{env}{env}{suffix}
    # Find the actual vault name in the resource group
    local vault_name
    vault_name=$(az keyvault list --resource-group "rg-pantrypilot-${TARGET_ENV}" --query "[0].name" -o tsv 2>/dev/null)

    if [[ -z "$vault_name" ]]; then
        log_error "Could not find Key Vault in rg-pantrypilot-${TARGET_ENV}"
        exit 1
    fi

    log_info "Fetching Azure connection from Key Vault: ${vault_name}"

    # Get connection string from Key Vault
    local conn_string
    conn_string=$(az keyvault secret show \
        --vault-name "$vault_name" \
        --name "dbConnectionString" \
        --query "value" \
        --output tsv 2>/dev/null) || {
        log_error "Failed to get connection string from Key Vault"
        log_info "Make sure you're logged in with: az login"
        exit 1
    }

    # Parse the connection string (format: postgresql://user:pass@host:port/database?sslmode=require)
    # Extract components using regex
    # pragma: allowlist nextline secret
    if [[ "$conn_string" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/([^?]+) ]]; then
        AZURE_USER="${BASH_REMATCH[1]}"
        AZURE_PASSWORD="${BASH_REMATCH[2]}"
        AZURE_HOST="${BASH_REMATCH[3]}"
        AZURE_PORT="${BASH_REMATCH[4]}"
        AZURE_DATABASE="${BASH_REMATCH[5]}"
    else
        log_error "Failed to parse connection string format"
        exit 1
    fi

    log_info "Target: ${AZURE_USER}@${AZURE_HOST}:${AZURE_PORT}/${AZURE_DATABASE}"
}

# Export data from source
export_data() {
    mkdir -p "$BACKUP_DIR"
    EXPORT_FILE="$BACKUP_DIR/pantrypilot_${SOURCE_TYPE}_export_${TIMESTAMP}.sql"

    log_step "Exporting data from source database..."

    local pg_dump_opts="--no-owner --no-privileges"

    if [[ "$INCLUDE_SCHEMA" == "true" ]]; then
        log_info "Including schema in export"
        pg_dump_opts="$pg_dump_opts --if-exists --clean"
    else
        pg_dump_opts="$pg_dump_opts --data-only"
        log_info "Exporting data only (schema must exist in target)"
    fi

    # Use --inserts for better compatibility
    pg_dump_opts="$pg_dump_opts --inserts --disable-triggers"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would export to: $EXPORT_FILE"
        return
    fi

    if [[ "$SOURCE_TYPE" == "docker" ]]; then
        # Export from Docker container
        docker exec pantrypilot-dev-db-1 pg_dump \
            -U "$SRC_USER" \
            -d "$SRC_DATABASE" \
            $pg_dump_opts \
            > "$EXPORT_FILE" || {
            log_error "Failed to export from Docker container"
            exit 1
        }
    else
        # Export from remote/local PostgreSQL
        PGPASSWORD="$SRC_PASSWORD" pg_dump \
            -h "$SRC_HOST" \
            -p "$SRC_PORT" \
            -U "$SRC_USER" \
            -d "$SRC_DATABASE" \
            $pg_dump_opts \
            > "$EXPORT_FILE" || {
            log_error "Failed to export from ${SRC_HOST}"
            exit 1
        }
    fi

    local file_size
    file_size=$(du -h "$EXPORT_FILE" | cut -f1)
    local line_count
    line_count=$(wc -l < "$EXPORT_FILE")

    log_success "Export complete: $EXPORT_FILE ($file_size, $line_count lines)"
}

# Run Alembic migrations on Azure to ensure schema is up to date
run_azure_migrations() {
    log_step "Running Alembic migrations on Azure to ensure schema is current..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run migrations"
        return
    fi

    cd "$PROJECT_ROOT/apps/backend"

    # Set the DATABASE_URL for Alembic (use asyncpg driver as expected by env.py)
    export DATABASE_URL="postgresql+asyncpg://${AZURE_USER}:${AZURE_PASSWORD}@${AZURE_HOST}:${AZURE_PORT}/${AZURE_DATABASE}?ssl=require"

    # Run migrations with explicit alembic.ini path
    uv run alembic -c src/alembic.ini upgrade head || {
        log_error "Failed to run migrations on Azure"
        exit 1
    }

    log_success "Migrations completed"
}

# Import data to Azure
import_data() {
    log_step "Importing data to Azure PostgreSQL..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would import from: $EXPORT_FILE"
        return
    fi

    log_info "Importing data..."

    # Use Docker PostgreSQL container for psql client if psql not available locally
    if command -v psql &>/dev/null; then
        PGPASSWORD="$AZURE_PASSWORD" psql \
            -h "$AZURE_HOST" \
            -p "$AZURE_PORT" \
            -U "$AZURE_USER" \
            -d "$AZURE_DATABASE" \
            --set ON_ERROR_STOP=off \
            -f "$EXPORT_FILE" 2>&1 | grep -v "^SET\|^$" | head -50 || true
    else
        log_info "Using Docker container for psql client..."
        # Copy export file to container and run psql
        docker cp "$EXPORT_FILE" pantrypilot-dev-db-1:/tmp/import.sql
        docker exec -e PGPASSWORD="$AZURE_PASSWORD" pantrypilot-dev-db-1 psql \
            -h "$AZURE_HOST" \
            -p "$AZURE_PORT" \
            -U "$AZURE_USER" \
            -d "$AZURE_DATABASE" \
            --set ON_ERROR_STOP=off \
            -f /tmp/import.sql 2>&1 | grep -v "^SET\|^$" | head -50 || true
        docker exec pantrypilot-dev-db-1 rm /tmp/import.sql
    fi

    # Verify import
    log_info "Verifying import..."
    local table_counts
    if command -v psql &>/dev/null; then
        table_counts=$(PGPASSWORD="$AZURE_PASSWORD" psql \
            -h "$AZURE_HOST" \
            -p "$AZURE_PORT" \
            -U "$AZURE_USER" \
            -d "$AZURE_DATABASE" \
            -t -c "
                SELECT
                    'users: ' || (SELECT COUNT(*) FROM users) ||
                    ', recipes: ' || (SELECT COUNT(*) FROM recipes) ||
                    ', meal_plans: ' || (SELECT COUNT(*) FROM meal_plans) ||
                    ', grocery_lists: ' || (SELECT COUNT(*) FROM grocery_lists)
            " 2>/dev/null) || {
            log_warn "Could not verify table counts"
            table_counts="Unable to verify"
        }
    else
        table_counts=$(docker exec -e PGPASSWORD="$AZURE_PASSWORD" pantrypilot-dev-db-1 psql \
            -h "$AZURE_HOST" \
            -p "$AZURE_PORT" \
            -U "$AZURE_USER" \
            -d "$AZURE_DATABASE" \
            -t -c "
                SELECT
                    'users: ' || (SELECT COUNT(*) FROM users) ||
                    ', recipes: ' || (SELECT COUNT(*) FROM recipes) ||
                    ', meal_plans: ' || (SELECT COUNT(*) FROM meal_plans) ||
                    ', grocery_lists: ' || (SELECT COUNT(*) FROM grocery_lists)
            " 2>/dev/null) || {
            log_warn "Could not verify table counts"
            table_counts="Unable to verify"
        }
    fi

    log_success "Import complete: $table_counts"
}

# Main execution
main() {
    echo ""
    echo "=============================================="
    echo "  PantryPilot - Migrate Data to Azure"
    echo "=============================================="
    echo ""

    parse_args "$@"
    validate_args

    # Get Azure connection (needed for both import and migration)
    if [[ "$SKIP_IMPORT" == "false" ]]; then
        get_azure_connection
    fi

    # Export phase
    if [[ "$SKIP_EXPORT" == "false" ]]; then
        configure_source
        export_data
    fi

    # Import phase
    if [[ "$SKIP_IMPORT" == "false" ]]; then
        # Run migrations to ensure schema exists
        run_azure_migrations

        # Import the data
        import_data
    fi

    echo ""
    log_success "Migration complete!"
    echo ""

    if [[ "$SKIP_IMPORT" == "false" ]]; then
        echo "You can verify the data at:"
        echo "  Frontend: https://lively-hill-0ee74371e.3.azurestaticapps.net"
        echo "  Backend:  https://pantrypilot-backend-${TARGET_ENV}.bravegrass-64b8c55f.centralus.azurecontainerapps.io/api/v1/health"
    fi

    if [[ -n "$EXPORT_FILE" && -f "$EXPORT_FILE" ]]; then
        echo ""
        echo "Export file saved: $EXPORT_FILE"
    fi
}

main "$@"
