-- PantryPilot Database Initialization Script
-- This script runs when the PostgreSQL container starts for the first time

-- =============================================================================
-- EXTENSIONS
-- =============================================================================
-- UUID generation for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Text search and similarity functions
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Statistics collection for query optimization
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Cryptographic functions (if needed for password hashing)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- UTILITY FUNCTIONS
-- =============================================================================

-- Health check function for monitoring
CREATE OR REPLACE FUNCTION health_check()
RETURNS TABLE(status TEXT, check_timestamp TIMESTAMP WITH TIME ZONE, database_name TEXT, version TEXT) AS $$
BEGIN
    RETURN QUERY SELECT
        'healthy'::TEXT as status,
        NOW() as check_timestamp,
        current_database()::TEXT as database_name,
        version()::TEXT as version;
END;
$$ LANGUAGE plpgsql;

-- Function to get database statistics
CREATE OR REPLACE FUNCTION db_stats()
RETURNS TABLE(
    database_size TEXT,
    active_connections INTEGER,
    total_tables INTEGER
) AS $$
BEGIN
    RETURN QUERY SELECT
        pg_size_pretty(pg_database_size(current_database())) as database_size,
        (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database())::INTEGER as active_connections,
        (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public')::INTEGER as total_tables;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- PERFORMANCE OPTIMIZATION FUNCTIONS
-- =============================================================================

-- Function to analyze table statistics (useful for query optimization)
CREATE OR REPLACE FUNCTION analyze_all_tables()
RETURNS TEXT AS $$
DECLARE
    table_name TEXT;
    result TEXT := '';
BEGIN
    FOR table_name IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE 'ANALYZE ' || quote_ident(table_name);
        result := result || 'Analyzed: ' || table_name || E'\n';
    END LOOP;

    IF result = '' THEN
        result := 'No user tables found to analyze';
    END IF;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- SECURITY SETUP
-- =============================================================================

-- Create application-specific user if running in development
-- (In production, this should be handled via environment variables)
DO $$
BEGIN
    -- Only create user if we're in a development environment
    -- Check if we're using a dev database name pattern
    IF current_database() LIKE '%dev%' OR current_database() LIKE '%development%' THEN
        -- Create readonly user for potential read replicas or reporting
        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'pantrypilot_readonly') THEN
            -- Use environment variable for password, or generate a random one for development
            PERFORM set_config('readonly_user_password',
                COALESCE(current_setting('readonly_user_password', true),
                md5(random()::text || clock_timestamp()::text)),
                false);

            CREATE USER pantrypilot_readonly WITH PASSWORD current_setting('readonly_user_password');
            GRANT CONNECT ON DATABASE pantrypilot_dev TO pantrypilot_readonly;
            GRANT USAGE ON SCHEMA public TO pantrypilot_readonly;
            -- Grant SELECT on all existing tables
            GRANT SELECT ON ALL TABLES IN SCHEMA public TO pantrypilot_readonly;
            -- Grant SELECT on all future tables
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO pantrypilot_readonly;

            RAISE NOTICE 'Created readonly user for development environment';
        END IF;
    END IF;
END $$;

-- =============================================================================
-- MONITORING SETUP
-- =============================================================================

-- Create a view for easy monitoring of database health
CREATE OR REPLACE VIEW db_health_monitor AS
SELECT
    'PantryPilot' as application,
    current_database() as database_name,
    version() as postgres_version,
    pg_size_pretty(pg_database_size(current_database())) as database_size,
    (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()) as active_connections,
    (SELECT setting FROM pg_settings WHERE name = 'max_connections') as max_connections,
    NOW() as last_checked;

-- Create a view for monitoring slow queries (requires pg_stat_statements)
CREATE OR REPLACE VIEW slow_queries_monitor AS
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time,
    rows
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- queries taking more than 100ms on average
ORDER BY mean_exec_time DESC
LIMIT 20;

-- =============================================================================
-- INITIALIZATION LOGGING
-- =============================================================================

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'PantryPilot Database Initialization';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Database: %', current_database();
    RAISE NOTICE 'User: %', current_user;
    RAISE NOTICE 'Timestamp: %', NOW();
    RAISE NOTICE 'Extensions installed: uuid-ossp, pg_trgm, pg_stat_statements, pgcrypto';
    RAISE NOTICE 'Health check function created: SELECT * FROM health_check();';
    RAISE NOTICE 'Database stats function created: SELECT * FROM db_stats();';
    RAISE NOTICE 'Monitoring views created: db_health_monitor, slow_queries_monitor';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Database initialization completed successfully!';
    RAISE NOTICE '========================================';
END $$;
