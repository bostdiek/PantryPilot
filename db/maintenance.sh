#!/bin/bash
# PantryPilot Database Maintenance Script
# This script performs routine database maintenance tasks

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
    echo "Usage: $0 [OPTIONS] COMMAND"
    echo ""
    echo "Commands:"
    echo "  analyze          Analyze all tables for query optimization"
    echo "  vacuum           Vacuum all tables to reclaim space"
    echo "  vacuum-full      Full vacuum (requires downtime)"
    echo "  reindex          Rebuild all indexes"
    echo "  stats            Show database statistics"
    echo "  health           Run health checks"
    echo "  slow-queries     Show slow queries (requires pg_stat_statements)"
    echo "  connections      Show active connections"
    echo "  size             Show database and table sizes"
    echo "  all              Run all maintenance tasks (analyze, vacuum)"
    echo ""
    echo "Options:"
    echo "  -e, --env ENV    Environment (dev|prod) [default: dev]"
    echo "  -v, --verbose    Verbose output"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 analyze                 # Analyze tables in development"
    echo "  $0 -e prod vacuum          # Vacuum production database"
    echo "  $0 -v stats                # Show verbose statistics"
    echo "  $0 all                     # Run all maintenance tasks"
}

# Default values
ENV="dev"
VERBOSE=false
COMMAND=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENV="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
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
            if [[ -z "$COMMAND" ]]; then
                COMMAND="$1"
            else
                print_error "Multiple commands specified. Please specify only one."
                exit 1
            fi
            shift
            ;;
    esac
done

# Check if command is specified
if [[ -z "$COMMAND" ]]; then
    print_error "No command specified"
    show_usage
    exit 1
fi

# Validate environment
if [[ "$ENV" != "dev" && "$ENV" != "prod" ]]; then
    print_error "Invalid environment: $ENV. Must be 'dev' or 'prod'"
    exit 1
fi

# Validate command
valid_commands=("analyze" "vacuum" "vacuum-full" "reindex" "stats" "health" "slow-queries" "connections" "size" "all")
if [[ ! " ${valid_commands[@]} " =~ " ${COMMAND} " ]]; then
    print_error "Invalid command: $COMMAND"
    show_usage
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

# Change to project directory
cd "$PROJECT_ROOT"

# Check if database service is running
if ! docker compose $COMPOSE_FILES ps db | grep -q "Up"; then
    print_error "Database service is not running. Please start it first:"
    print_error "  make ENV=$ENV up"
    exit 1
fi

# Function to execute SQL commands
execute_sql() {
    local sql="$1"
    local output_format="${2:-text}"

    if [[ "$VERBOSE" == true ]]; then
        print_status "Executing: $sql"
    fi

    if [[ "$output_format" == "table" ]]; then
        docker compose $COMPOSE_FILES exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$sql"
    else
        docker compose $COMPOSE_FILES exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "$sql" | tr -d '\r'
    fi
}

# Function to execute SQL from a file or string with timing
execute_timed_sql() {
    local sql="$1"
    local description="$2"

    print_status "$description..."
    local start_time=$(date +%s)

    execute_sql "$sql" > /dev/null 2>&1

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    print_success "$description completed in ${duration}s"
}

# Header
print_status "🔧 PantryPilot Database Maintenance"
print_status "Environment: $ENV"
print_status "Database: $POSTGRES_DB"
print_status "Command: $COMMAND"
echo ""

# Execute commands
case $COMMAND in
    "analyze")
        execute_timed_sql "ANALYZE;" "Analyzing all tables"
        ;;

    "vacuum")
        execute_timed_sql "VACUUM;" "Vacuuming all tables"
        ;;

    "vacuum-full")
        print_warning "⚠️  Full vacuum requires exclusive locks and may cause downtime!"
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            execute_timed_sql "VACUUM FULL;" "Performing full vacuum"
        else
            print_status "Full vacuum cancelled"
        fi
        ;;

    "reindex")
        print_warning "⚠️  Reindexing may cause performance impact during execution!"
        execute_timed_sql "REINDEX DATABASE \"$POSTGRES_DB\";" "Rebuilding all indexes"
        ;;

    "stats")
        print_status "📊 Database Statistics"
        echo ""

        # Database overview
        print_status "Database Overview:"
        execute_sql "
            SELECT
                current_database() as database_name,
                pg_size_pretty(pg_database_size(current_database())) as database_size,
                (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public') as table_count,
                (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()) as active_connections,
                (SELECT setting FROM pg_settings WHERE name = 'max_connections') as max_connections;
        " table

        echo ""
        print_status "Table Sizes:"
        execute_sql "
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        " table
        ;;

    "health")
        print_status "🏥 Database Health Check"
        echo ""

        # Check if health_check function exists
        if execute_sql "SELECT 1 FROM pg_proc WHERE proname = 'health_check';" | grep -q 1; then
            print_status "Running custom health check:"
            execute_sql "SELECT * FROM health_check();" table
        else
            print_warning "Custom health_check function not found"
        fi

        # Basic connectivity test
        print_status "Basic connectivity:"
        execute_sql "SELECT 'Database connection successful' as status, NOW() as timestamp;" table

        # Check for monitoring views
        if execute_sql "SELECT 1 FROM pg_views WHERE viewname = 'db_health_monitor';" | grep -q 1; then
            echo ""
            print_status "Health monitoring view:"
            execute_sql "SELECT * FROM db_health_monitor;" table
        fi
        ;;

    "slow-queries")
        print_status "🐌 Slow Queries Analysis"
        echo ""

        # Check if pg_stat_statements extension is available
        if execute_sql "SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements';" | grep -q 1; then
            if execute_sql "SELECT 1 FROM pg_views WHERE viewname = 'slow_queries_monitor';" | grep -q 1; then
                execute_sql "SELECT * FROM slow_queries_monitor;" table
            else
                print_status "Top 10 slowest queries:"
                execute_sql "
                    SELECT
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        max_exec_time
                    FROM pg_stat_statements
                    ORDER BY mean_exec_time DESC
                    LIMIT 10;
                " table
            fi
        else
            print_warning "pg_stat_statements extension not available"
        fi
        ;;

    "connections")
        print_status "🔗 Active Connections"
        echo ""

        execute_sql "
            SELECT
                pid,
                usename,
                application_name,
                client_addr,
                backend_start,
                state,
                query_start,
                LEFT(query, 50) as current_query
            FROM pg_stat_activity
            WHERE datname = current_database()
            ORDER BY backend_start;
        " table
        ;;

    "size")
        print_status "💾 Database Size Information"
        echo ""

        print_status "Database Size:"
        execute_sql "
            SELECT
                pg_size_pretty(pg_database_size(current_database())) as total_size;
        " table

        echo ""
        print_status "Largest Tables:"
        execute_sql "
            SELECT
                tablename,
                pg_size_pretty(pg_total_relation_size('public.'||tablename)) as total_size,
                pg_size_pretty(pg_relation_size('public.'||tablename)) as table_size,
                pg_size_pretty(pg_total_relation_size('public.'||tablename) - pg_relation_size('public.'||tablename)) as index_size
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size('public.'||tablename) DESC
            LIMIT 10;
        " table
        ;;

    "all")
        print_status "🔄 Running All Maintenance Tasks"
        echo ""

        execute_timed_sql "ANALYZE;" "Analyzing all tables"
        execute_timed_sql "VACUUM;" "Vacuuming all tables"

        echo ""
        print_success "All maintenance tasks completed!"
        ;;
esac

echo ""
print_success "✅ Maintenance operation completed successfully!"
