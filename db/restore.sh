#!/bin/bash
# PantryPilot Database Restore Script
# This script restores PostgreSQL database from backup files

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] BACKUP_FILE"
    echo ""
    echo "Options:"
    echo "  -e, --env ENV         Target environment (dev|prod) [default: dev]"
    echo "  -f, --force          Force restore without confirmation"
    echo "  --clean              Drop existing database before restore"
    echo "  --create             Create database if it doesn't exist"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 backup.sql                    # Restore to development environment"
    echo "  $0 -e prod backup.sql            # Restore to production environment"
    echo "  $0 --clean --create backup.sql   # Clean restore with database recreation"
    echo "  $0 -f backup.sql.gz              # Force restore from compressed backup"
    echo ""
    echo "Available backups in $BACKUP_DIR:"
    if [[ -d "$BACKUP_DIR" ]]; then
        ls -1 "$BACKUP_DIR"/*.sql* 2>/dev/null | head -10 || echo "  No backup files found"
    else
        echo "  Backup directory not found"
    fi
}

# Default values
ENV="dev"
FORCE=false
CLEAN=false
CREATE=false
BACKUP_FILE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENV="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --create)
            CREATE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$BACKUP_FILE" ]]; then
                BACKUP_FILE="$1"
            else
                print_error "Multiple backup files specified. Please specify only one."
                exit 1
            fi
            shift
            ;;
    esac
done

# Check if backup file is specified
if [[ -z "$BACKUP_FILE" ]]; then
    print_error "No backup file specified"
    show_usage
    exit 1
fi

# Validate environment
if [[ "$ENV" != "dev" && "$ENV" != "prod" ]]; then
    print_error "Invalid environment: $ENV. Must be 'dev' or 'prod'"
    exit 1
fi

# Set environment file and compose files
if [[ "$ENV" == "prod" ]]; then
    ENV_FILE="$PROJECT_ROOT/.env.prod"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
else
    ENV_FILE="$PROJECT_ROOT/.env.dev"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.dev.yml"
fi

# Check if environment file exists
if [[ ! -f "$ENV_FILE" ]]; then
    print_error "Environment file not found: $ENV_FILE"
    exit 1
fi

# Load environment variables
print_status "Loading environment variables from $ENV_FILE"
set -a  # Automatically export all variables
source "$ENV_FILE"
set +a

# Resolve backup file path
if [[ ! -f "$BACKUP_FILE" ]]; then
    # Try to find in backup directory
    if [[ -f "$BACKUP_DIR/$BACKUP_FILE" ]]; then
        BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
    else
        print_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
fi

# Check if backup file exists and is readable
if [[ ! -r "$BACKUP_FILE" ]]; then
    print_error "Cannot read backup file: $BACKUP_FILE"
    exit 1
fi

# Determine if file is compressed
COMPRESSED=false
if [[ "$BACKUP_FILE" == *.gz ]]; then
    COMPRESSED=true
fi

print_status "Restore configuration:"
print_status "  Environment: $ENV"
print_status "  Database: $POSTGRES_DB"
print_status "  User: $POSTGRES_USER"
print_status "  Backup file: $BACKUP_FILE"
print_status "  Compressed: $COMPRESSED"
print_status "  Clean restore: $CLEAN"
print_status "  Create database: $CREATE"

# Change to project directory
cd "$PROJECT_ROOT"

# Check if database service is running
if ! docker compose $COMPOSE_FILES ps db | grep -q "Up"; then
    print_error "Database service is not running. Please start it first:"
    print_error "  make ENV=$ENV up"
    exit 1
fi

# Confirmation prompt (unless force is specified)
if [[ "$FORCE" != true ]]; then
    echo ""
    print_warning "⚠️  WARNING: This will restore the database and may overwrite existing data!"
    if [[ "$CLEAN" == true ]]; then
        print_warning "⚠️  WARNING: --clean option will DROP ALL EXISTING DATA first!"
    fi
    echo ""
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Restore cancelled by user"
        exit 0
    fi
fi

# Function to execute SQL commands
execute_sql() {
    docker compose $COMPOSE_FILES exec -T db psql -U "$POSTGRES_USER" -d postgres -c "$1"
}

# Function to execute SQL from file
execute_sql_file() {
    if [[ "$COMPRESSED" == true ]]; then
        gunzip -c "$BACKUP_FILE" | docker compose $COMPOSE_FILES exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" --quiet
    else
        docker compose $COMPOSE_FILES exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" --quiet < "$BACKUP_FILE"
    fi
}

# Pre-restore steps
if [[ "$CLEAN" == true ]]; then
    print_status "Dropping existing database: $POSTGRES_DB"
    execute_sql "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";"
fi

if [[ "$CREATE" == true ]] || [[ "$CLEAN" == true ]]; then
    print_status "Creating database: $POSTGRES_DB"
    execute_sql "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\";"
fi

# Perform the restore
print_status "Starting database restore..."
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
print_status "Restoring from backup file ($BACKUP_SIZE)..."

# Execute the restore
if execute_sql_file; then
    print_success "Database restore completed successfully!"

    # Show restore statistics
    print_status "Post-restore information:"

    # Get table count and database size
    TABLE_COUNT=$(docker compose $COMPOSE_FILES exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d '\r' | xargs)
    DB_SIZE=$(docker compose $COMPOSE_FILES exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT pg_size_pretty(pg_database_size('$POSTGRES_DB'));" | tr -d '\r' | xargs)

    print_success "  Tables restored: $TABLE_COUNT"
    print_success "  Database size: $DB_SIZE"

    # Run database health check if available
    if docker compose $COMPOSE_FILES exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT 1 FROM pg_proc WHERE proname = 'health_check';" | grep -q 1; then
        print_status "Running health check..."
        HEALTH_RESULT=$(docker compose $COMPOSE_FILES exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT status FROM health_check();" | tr -d '\r' | xargs)
        print_success "  Health check: $HEALTH_RESULT"
    fi

    # Analyze tables for optimal performance
    print_status "Analyzing tables for optimal performance..."
    docker compose $COMPOSE_FILES exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "ANALYZE;" >/dev/null
    print_success "Database analysis completed"

else
    print_error "Database restore failed!"
    exit 1
fi

print_success "✅ Restore operation completed successfully!"
