# PantryPilot Database Setup

This directory contains the PostgreSQL database configuration, initialization scripts, and maintenance tools for PantryPilot.

## 📁 Directory Structure

```
db/
├── README.md                 # This file
├── backup.sh                 # Database backup script
├── restore.sh                # Database restore script
├── maintenance.sh            # Database maintenance script
├── docker-compose.yml        # Legacy - now in project root
├── entrypoint.sh             # Database initialization entrypoint
├── schema.sql                # Legacy - now in init/
└── init/                     # Database initialization scripts
    ├── 01-init.sql           # Extensions and utility functions
    └── 02-schema-setup.sql   # Application schema and sample data
```

## 🚀 Quick Start

### 1. Start the Database
```bash
# Development environment
make up

# Production environment
make ENV=prod up
```

### 2. Check Database Health
```bash
./db/maintenance.sh health
```

### 3. Create a Backup
```bash
./db/backup.sh
```

## 🔧 Database Scripts

### Backup Script (`backup.sh`)

Creates backups of the PostgreSQL database with various options.

**Usage:**
```bash
./db/backup.sh [OPTIONS]

Options:
  -e, --env ENV         Environment (dev|prod) [default: dev]
  -t, --type TYPE       Backup type (full|data|schema) [default: full]
  -o, --output DIR      Output directory [default: ./backups]
  -c, --compress        Compress backup file
  -h, --help           Show help message
```

**Examples:**
```bash
# Create full development backup
./db/backup.sh

# Create compressed production backup
./db/backup.sh -e prod -c

# Create data-only backup
./db/backup.sh -t data

# Create schema-only backup to custom directory
./db/backup.sh -t schema -o /path/to/backups
```

### Restore Script (`restore.sh`)

Restores PostgreSQL database from backup files.

**Usage:**
```bash
./db/restore.sh [OPTIONS] BACKUP_FILE

Options:
  -e, --env ENV         Target environment (dev|prod) [default: dev]
  -f, --force          Force restore without confirmation
  --clean              Drop existing database before restore
  --create             Create database if it doesn't exist
  -h, --help           Show help message
```

**Examples:**
```bash
# Restore to development environment
./db/restore.sh backup.sql

# Restore to production with clean slate
./db/restore.sh -e prod --clean --create backup.sql

# Force restore from compressed backup
./db/restore.sh -f backup.sql.gz
```

### Maintenance Script (`maintenance.sh`)

Performs routine database maintenance and monitoring tasks.

**Usage:**
```bash
./db/maintenance.sh [OPTIONS] COMMAND

Commands:
  analyze          Analyze all tables for query optimization
  vacuum           Vacuum all tables to reclaim space
  vacuum-full      Full vacuum (requires downtime)
  reindex          Rebuild all indexes
  stats            Show database statistics
  health           Run health checks
  slow-queries     Show slow queries (requires pg_stat_statements)
  connections      Show active connections
  size             Show database and table sizes
  all              Run all maintenance tasks (analyze, vacuum)
```

**Examples:**
```bash
# Analyze tables for better performance
./db/maintenance.sh analyze

# Show database statistics
./db/maintenance.sh -v stats

# Run all maintenance tasks on production
./db/maintenance.sh -e prod all

# Check for slow queries
./db/maintenance.sh slow-queries
```

## 🗃️ Database Schema

> **⚠️ IMPORTANT NOTE**: The current database schema is **for demonstration and end-to-end testing purposes only**. This is a basic structure to validate our Docker Compose setup, database connectivity, and development workflows.
>
> **The actual production schema for the AI-powered recipe recommendation system will be designed collaboratively later** based on the specific requirements for ingredient analysis, recipe matching, nutritional data, and AI model integration.

### Current Demo Tables

1. **`users`** - Basic user authentication (demo structure)
2. **`pantry_items`** - Simple pantry inventory (demo structure)
3. **`recipes`** - Basic recipe definitions (demo structure)
4. **`recipe_ingredients`** - Simple recipe ingredient relationships (demo structure)

### Planned AI Schema Features

The production schema will be designed to support:
- Advanced ingredient taxonomy and categorization
- Nutritional data integration
- Recipe complexity scoring for AI recommendations
- User preference learning and dietary restrictions
- Inventory optimization algorithms
- Recipe suggestion ranking and feedback loops

### Key Features

- **UUID Primary Keys** for better scalability
- **Automatic Timestamps** with triggers for `updated_at`
- **Full-Text Search** capabilities with `pg_trgm` extension
- **Performance Indexes** for common query patterns
- **Sample Data** in development environment

### Useful Functions

- **`health_check()`** - Returns database health status
- **`db_stats()`** - Returns database statistics
- **`analyze_all_tables()`** - Analyzes all tables for optimization

### Monitoring Views

- **`db_health_monitor`** - Database health overview
- **`slow_queries_monitor`** - Slow query analysis (requires `pg_stat_statements`)

## 🔐 Security Features

### Development Environment
- Simple passwords for easy local development
- Port 5432 exposed for database tools
- Detailed query logging for debugging
- Sample data included

### Production Environment
- Strong randomly generated passwords
- No exposed ports (internal access only)
- Optimized logging levels
- Performance-tuned configuration
- Security hardening enabled

## 📊 Performance Optimization

### Automated Optimizations
- **Shared Buffers**: 256MB in production
- **Effective Cache Size**: 1GB in production
- **WAL Buffers**: 16MB for write performance
- **Work Memory**: 4MB per operation
- **Max Connections**: 200 concurrent connections

### Manual Optimizations
```bash
# Analyze tables after bulk operations
./db/maintenance.sh analyze

# Vacuum tables to reclaim space
./db/maintenance.sh vacuum

# Full vacuum during maintenance windows
./db/maintenance.sh vacuum-full
```

## 🔄 Backup Strategy

### Recommended Schedule
- **Development**: Weekly full backups
- **Production**:
  - Daily full backups
  - Hourly incremental backups (if implemented)
  - Monthly compressed archives

### Backup Types
- **Full Backup**: Complete database with schema and data
- **Data Only**: Just the data (for schema migrations)
- **Schema Only**: Just the structure (for development setup)

### Retention Policy
- **Daily backups**: Keep for 30 days
- **Weekly backups**: Keep for 3 months
- **Monthly backups**: Keep for 1 year

## 🚨 Troubleshooting

### Common Issues

**Database won't start:**
```bash
# Check Docker Compose status
make ENV=dev up
docker compose logs db

# Check disk space
df -h

# Reset database if corrupted
make ENV=dev reset-db
```

**Connection refused:**
```bash
# Verify service is running
docker compose ps

# Check network connectivity
docker compose exec backend ping db

# Verify environment variables
cat .env.dev | grep POSTGRES
```

**Poor performance:**
```bash
# Analyze tables
./db/maintenance.sh analyze

# Check for slow queries
./db/maintenance.sh slow-queries

# Show database statistics
./db/maintenance.sh stats
```

**Disk space issues:**
```bash
# Check database size
./db/maintenance.sh size

# Vacuum to reclaim space
./db/maintenance.sh vacuum

# Full vacuum if needed (during maintenance window)
./db/maintenance.sh vacuum-full
```

### Recovery Procedures

**Data corruption:**
1. Stop the application
2. Restore from latest backup
3. Verify data integrity
4. Restart application

**Schema migration issues:**
1. Create schema backup before migration
2. Test migration on development copy
3. Apply migration with rollback plan
4. Verify application functionality

## 📈 Monitoring

### Health Checks
```bash
# Quick health check
./db/maintenance.sh health

# Detailed statistics
./db/maintenance.sh stats

# Connection monitoring
./db/maintenance.sh connections
```

### Performance Monitoring
```bash
# Database size tracking
./db/maintenance.sh size

# Slow query analysis
./db/maintenance.sh slow-queries

# Index usage statistics
docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public';"
```

## 🧪 Development Tips

### Connecting with Database Tools
```bash
# Connection parameters for development
Host: localhost
Port: 5432
Database: pantrypilot_dev
Username: pantrypilot_dev
Password: dev_password_123
```

### Useful SQL Queries
```sql
-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check active connections
SELECT pid, usename, application_name, client_addr, state, query_start
FROM pg_stat_activity
WHERE datname = current_database();

-- Run health check
SELECT * FROM health_check();
```

### Reset Development Data
```bash
# Reset database and reload sample data
make ENV=dev reset-db

# Or manually
docker compose down -v
docker compose up -d db
```

## 📝 Migration Guidelines

### Schema Changes
1. Create migration script in `db/migrations/`
2. Test on development environment
3. Create backup before production migration
4. Apply migration during maintenance window
5. Verify application compatibility

### Data Migrations
1. Export data with `./db/backup.sh -t data`
2. Transform data as needed
3. Test import on development copy
4. Schedule production migration
5. Validate data integrity

---

## 🆘 Support

For issues related to database setup or maintenance:

1. Check this README for common solutions
2. Review Docker Compose logs: `docker compose logs db`
3. Run health checks: `./db/maintenance.sh health`
4. Create an issue in the project repository

Remember to include relevant logs and environment details when reporting issues.
