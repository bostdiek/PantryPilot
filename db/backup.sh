#!/bin/bash
# PantryPilot Database Backup Script
# This script creates backups of the PostgreSQL database

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

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
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --env ENV         Environment (dev|prod) [default: dev]"
    echo "  -t, --type TYPE       Backup type (full|data|schema) [default: full]"
    echo "  -o, --output DIR      Output directory [default: ./backups]"
    echo "  -c, --compress        Compress backup file"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Create full development backup"
    echo "  $0 -e prod -t data    # Create production data-only backup"
    echo "  $0 -c                 # Create compressed backup"
}

# Default values
ENV="dev"
BACKUP_TYPE="full"
COMPRESS=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENV="$2"
            shift 2
            ;;
        -t|--type)
            BACKUP_TYPE="$2"
            shift 2
            ;;
        -o|--output)
            BACKUP_DIR="$2"
            shift 2
            ;;
        -c|--compress)
            COMPRESS=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENV" != "dev" && "$ENV" != "prod" ]]; then
    print_error "Invalid environment: $ENV. Must be 'dev' or 'prod'"
    exit 1
fi

# Validate backup type
if [[ "$BACKUP_TYPE" != "full" && "$BACKUP_TYPE" != "data" && "$BACKUP_TYPE" != "schema" ]]; then
    print_error "Invalid backup type: $BACKUP_TYPE. Must be 'full', 'data', or 'schema'"
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

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename
BACKUP_FILENAME="pantrypilot_${ENV}_${BACKUP_TYPE}_${TIMESTAMP}"
if [[ "$COMPRESS" == true ]]; then
    BACKUP_FILE="$BACKUP_DIR/${BACKUP_FILENAME}.sql.gz"
else
    BACKUP_FILE="$BACKUP_DIR/${BACKUP_FILENAME}.sql"
fi

print_status "Starting $BACKUP_TYPE backup for $ENV environment"
print_status "Output file: $BACKUP_FILE"

# Change to project directory
cd "$PROJECT_ROOT"

# Check if database service is running
if ! docker compose $COMPOSE_FILES ps db | grep -q "Up"; then
    print_error "Database service is not running. Please start it first:"
    print_error "  make ENV=$ENV up"
    exit 1
fi

# Perform backup based on type
case $BACKUP_TYPE in
    "full")
        print_status "Creating full backup (schema + data)"
        if [[ "$COMPRESS" == true ]]; then
            docker compose $COMPOSE_FILES exec -T db pg_dump \
                -U "$POSTGRES_USER" \
                -d "$POSTGRES_DB" \
                --verbose \
                --no-password | gzip > "$BACKUP_FILE"
        else
            docker compose $COMPOSE_FILES exec -T db pg_dump \
                -U "$POSTGRES_USER" \
                -d "$POSTGRES_DB" \
                --verbose \
                --no-password > "$BACKUP_FILE"
        fi
        ;;
    "data")
        print_status "Creating data-only backup"
        if [[ "$COMPRESS" == true ]]; then
            docker compose $COMPOSE_FILES exec -T db pg_dump \
                -U "$POSTGRES_USER" \
                -d "$POSTGRES_DB" \
                --data-only \
                --verbose \
                --no-password | gzip > "$BACKUP_FILE"
        else
            docker compose $COMPOSE_FILES exec -T db pg_dump \
                -U "$POSTGRES_USER" \
                -d "$POSTGRES_DB" \
                --data-only \
                --verbose \
                --no-password > "$BACKUP_FILE"
        fi
        ;;
    "schema")
        print_status "Creating schema-only backup"
        if [[ "$COMPRESS" == true ]]; then
            docker compose $COMPOSE_FILES exec -T db pg_dump \
                -U "$POSTGRES_USER" \
                -d "$POSTGRES_DB" \
                --schema-only \
                --verbose \
                --no-password | gzip > "$BACKUP_FILE"
        else
            docker compose $COMPOSE_FILES exec -T db pg_dump \
                -U "$POSTGRES_USER" \
                -d "$POSTGRES_DB" \
                --schema-only \
                --verbose \
                --no-password > "$BACKUP_FILE"
        fi
        ;;
esac

# Check if backup was successful
if [[ $? -eq 0 ]]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    print_success "Backup completed successfully!"
    print_success "File: $BACKUP_FILE"
    print_success "Size: $BACKUP_SIZE"

    # Create a metadata file
    METADATA_FILE="${BACKUP_FILE}.meta"
    cat > "$METADATA_FILE" << EOF
# PantryPilot Database Backup Metadata
backup_date=$(date -Iseconds)
backup_type=$BACKUP_TYPE
environment=$ENV
database_name=$POSTGRES_DB
database_user=$POSTGRES_USER
compressed=$COMPRESS
backup_file=$(basename "$BACKUP_FILE")
backup_size=$BACKUP_SIZE
postgres_version=$(docker compose $COMPOSE_FILES exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT version();" | tr -d '\r' | xargs)
EOF

    print_success "Metadata saved to: $METADATA_FILE"

    # List recent backups
    print_status "Recent backups in $BACKUP_DIR:"
    ls -lah "$BACKUP_DIR"/*.sql* 2>/dev/null | tail -5 || print_warning "No previous backups found"

else
    print_error "Backup failed!"
    exit 1
fi
