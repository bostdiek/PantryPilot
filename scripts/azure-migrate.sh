#!/bin/bash
# =============================================================================
# Azure Database Migration Script for PantryPilot
# =============================================================================
# This script runs Alembic migrations against Azure PostgreSQL Flexible Server
# It's designed to be called from GitHub Actions or manually for troubleshooting
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Validate required environment variables
validate_env() {
    local missing=0

    if [[ -z "${AZURE_SUBSCRIPTION_ID:-}" ]]; then
        log_error "AZURE_SUBSCRIPTION_ID is not set"
        missing=1
    fi

    if [[ -z "${DEPLOY_ENV:-}" ]]; then
        log_error "DEPLOY_ENV is not set (expected: dev or prod)"
        missing=1
    fi

    if [[ $missing -eq 1 ]]; then
        exit 1
    fi
}

# Get database connection string from Key Vault
get_connection_string() {
    local env="${1:-dev}"
    # Key Vault name follows Bicep naming: ppkv${environmentName}${uniqueSuffix}
    local vault_name="ppkv${env}${env}001"

    log_info "Fetching database connection string from Key Vault: ${vault_name}"

    local connection_string
    connection_string=$(az keyvault secret show \
        --vault-name "$vault_name" \
        --name "dbConnectionString" \
        --query "value" \
        --output tsv 2>/dev/null)

    if [[ -z "$connection_string" ]]; then
        log_error "Failed to retrieve connection string from Key Vault"
        exit 1
    fi

    echo "$connection_string"
}

# Run Alembic migrations
run_migrations() {
    local connection_string="$1"

    log_info "Running Alembic migrations..."

    # Change to backend directory
    cd "$(dirname "$0")/../apps/backend"

    # Export the connection string
    export DATABASE_URL="$connection_string"

    # Check current revision
    log_info "Current database revision:"
    uv run alembic current || log_warn "Could not determine current revision (database may be empty)"

    # Show pending migrations
    log_info "Pending migrations:"
    uv run alembic history --verbose | head -20

    # Run migrations
    log_info "Applying migrations..."
    uv run alembic upgrade head

    # Verify final state
    log_info "Final database revision:"
    uv run alembic current

    log_info "Migrations completed successfully!"
}

# Rollback migrations (for emergency use)
rollback_migration() {
    local connection_string="$1"
    local target="${2:--1}"  # Default: rollback one revision

    log_warn "Rolling back migrations to: ${target}"

    cd "$(dirname "$0")/../apps/backend"
    export DATABASE_URL="$connection_string"

    uv run alembic downgrade "$target"

    log_info "Rollback completed. Current revision:"
    uv run alembic current
}

# Main function
main() {
    local action="${1:-migrate}"
    local env="${DEPLOY_ENV:-dev}"

    log_info "PantryPilot Azure Migration Script"
    log_info "Environment: ${env}"
    log_info "Action: ${action}"

    validate_env

    # Ensure we're logged into Azure
    if ! az account show &>/dev/null; then
        log_error "Not logged into Azure. Please run 'az login' first."
        exit 1
    fi

    # Get connection string
    local connection_string
    connection_string=$(get_connection_string "$env")

    case "$action" in
        migrate)
            run_migrations "$connection_string"
            ;;
        rollback)
            rollback_migration "$connection_string" "${2:--1}"
            ;;
        current)
            cd "$(dirname "$0")/../apps/backend"
            export DATABASE_URL="$connection_string"
            uv run alembic current
            ;;
        history)
            cd "$(dirname "$0")/../apps/backend"
            export DATABASE_URL="$connection_string"
            uv run alembic history --verbose
            ;;
        *)
            log_error "Unknown action: ${action}"
            echo "Usage: $0 [migrate|rollback|current|history] [rollback_target]"
            exit 1
            ;;
    esac
}

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
