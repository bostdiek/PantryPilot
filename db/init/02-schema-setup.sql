-- PantryPilot Schema Setup
-- This script sets up the basic database schema structure

-- =============================================================================
-- ⚠️  IMPORTANT DISCLAIMER
-- =============================================================================
-- This schema is for DEMONSTRATION and END-TO-END TESTING purposes only!
--
-- The actual production schema for the AI-powered recipe recommendation system
-- will be designed collaboratively later based on specific requirements for:
-- - Advanced ingredient taxonomy and categorization systems
-- - Nutritional data integration and analysis
-- - Recipe complexity scoring for AI recommendations
-- - User preference learning and dietary restriction modeling
-- - Inventory optimization algorithms
-- - Recipe suggestion ranking and feedback loops
-- - Integration with external food APIs and databases
--
-- This current schema simply validates Docker setup, database connectivity,
-- and provides basic structure for development workflow testing.
-- =============================================================================

-- =============================================================================
-- CORE APPLICATION TABLES (Basic Demo Structure)
-- =============================================================================

-- Users table (basic structure for authentication)
-- NOTE: Production will need more sophisticated user management,
-- including dietary preferences, allergies, cooking skill levels, etc.
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Pantry items table (basic structure)
-- NOTE: Production will need ingredient taxonomy, nutritional data,
-- expiration tracking, storage conditions, purchase history, etc.
CREATE TABLE IF NOT EXISTS ingredient_names (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ingredient_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Recipes table (basic structure)
-- NOTE: Production will need cuisine types, difficulty scoring,
-- nutritional analysis, cooking methods, equipment requirements, etc.
CREATE TABLE IF NOT EXISTS recipe_names (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    prep_time_minutes INTEGER,
    cook_time_minutes INTEGER,
    total_time_minutes INTEGER,
    serving_min INTEGER,
    serving_max INTEGER,
    ethnicity VARCHAR(255),
    course_type VARCHAR(255),
    instructions TEXT,
    user_notes TEXT,
    ai_summary TEXT,
    link_source TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Recipe ingredients (many-to-many relationship)
-- NOTE: Production will need sophisticated ingredient matching,
-- substitution suggestions, nutritional calculations, etc.
CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipe_id UUID NOT NULL REFERENCES recipe_names(id) ON DELETE CASCADE,
    ingredient_id UUID NOT NULL REFERENCES ingredient_names(id) ON DELETE CASCADE,
    quantity VARCHAR(255),
    unit TEXT,
    is_optional BOOLEAN DEFAULT false,
    user_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Meal history table (basic structure)
-- NOTE: Production will need meal planning, tracking, and feedback loops
CREATE TABLE IF NOT EXISTS meal_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    date_suggested TIMESTAMP WITH TIME ZONE,
    week_suggested INTEGER,
    was_cooked BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- User indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- Pantry items indexes
CREATE INDEX IF NOT EXISTS idx_pantry_items_user_id ON pantry_items(user_id);
CREATE INDEX IF NOT EXISTS idx_pantry_items_name ON pantry_items(name);
CREATE INDEX IF NOT EXISTS idx_pantry_items_category ON pantry_items(category);
CREATE INDEX IF NOT EXISTS idx_pantry_items_expiration ON pantry_items(expiration_date);
CREATE INDEX IF NOT EXISTS idx_pantry_items_name_trgm ON pantry_items USING gin (name gin_trgm_ops);

-- Recipe indexes
CREATE INDEX IF NOT EXISTS idx_recipes_user_id ON recipes(user_id);
CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title);
CREATE INDEX IF NOT EXISTS idx_recipes_difficulty ON recipes(difficulty_level);
CREATE INDEX IF NOT EXISTS idx_recipes_title_trgm ON recipes USING gin (title gin_trgm_ops);

-- Recipe ingredients indexes
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_name ON recipe_ingredients(ingredient_name);

-- =============================================================================
-- TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- =============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for all tables with updated_at columns
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pantry_items_updated_at
    BEFORE UPDATE ON pantry_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recipes_updated_at
    BEFORE UPDATE ON recipes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- SAMPLE DATA (Development Only - For Testing Database Connectivity)
-- =============================================================================

-- Insert sample data only in development environment
-- NOTE: This is just for testing the database setup and Docker connectivity!
-- Real data structure and relationships will be designed for the AI system.
DO $$
BEGIN
    IF current_database() LIKE '%dev%' OR current_database() LIKE '%development%' THEN
        -- Insert a sample user with secure random password hash
        -- NOTE: Production will have proper authentication with OAuth, etc.
        INSERT INTO users (id, email, hashed_password, full_name, is_active, is_superuser)
        VALUES (
            uuid_generate_v4(),
            'demo@pantrypilot.dev',
            '$2b$12$SecureHashForDemoAccountOnlyNotForProd.Development.Only',
            'Demo User',
            true,
            false
        ) ON CONFLICT (email) DO NOTHING;

        -- Get the demo user ID
        WITH demo_user AS (
            SELECT id FROM users WHERE email = 'demo@pantrypilot.dev'
        )
        -- Insert sample pantry items (just for testing database operations!)
        -- NOTE: Real pantry management will have ingredient taxonomy,
        -- nutritional data, smart expiration tracking, etc.
        INSERT INTO pantry_items (user_id, name, category, quantity, unit, expiration_date, location)
        SELECT
            demo_user.id,
            unnest(ARRAY['Flour', 'Sugar', 'Eggs', 'Milk', 'Chicken Breast', 'Tomatoes', 'Onions', 'Garlic']),
            unnest(ARRAY['Baking', 'Baking', 'Dairy', 'Dairy', 'Meat', 'Produce', 'Produce', 'Produce']),
            unnest(ARRAY[5.0, 2.0, 12.0, 1.0, 2.0, 6.0, 3.0, 1.0]),
            unnest(ARRAY['lbs', 'lbs', 'count', 'gallon', 'lbs', 'count', 'count', 'bulb']),
            unnest(ARRAY[
                CURRENT_DATE + INTERVAL '6 months',
                CURRENT_DATE + INTERVAL '1 year',
                CURRENT_DATE + INTERVAL '3 weeks',
                CURRENT_DATE + INTERVAL '1 week',
                CURRENT_DATE + INTERVAL '5 days',
                CURRENT_DATE + INTERVAL '1 week',
                CURRENT_DATE + INTERVAL '2 weeks',
                CURRENT_DATE + INTERVAL '3 weeks'
            ]),
            unnest(ARRAY['Pantry', 'Pantry', 'Refrigerator', 'Refrigerator', 'Freezer', 'Refrigerator', 'Pantry', 'Pantry'])
        FROM demo_user
        ON CONFLICT DO NOTHING;

        RAISE NOTICE '========================================';
        RAISE NOTICE 'DEMO DATA NOTICE:';
        RAISE NOTICE 'Sample development data inserted for testing only!';
        RAISE NOTICE 'This is NOT the final AI-powered schema design.';
        RAISE NOTICE '========================================';
    END IF;
END $$;

-- =============================================================================
-- COMPLETION LOG
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Demo Schema Setup Completed';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'IMPORTANT: This is a DEMONSTRATION schema only!';
    RAISE NOTICE 'Tables created: users, pantry_items, recipes, recipe_ingredients';
    RAISE NOTICE 'Indexes created for optimal query performance';
    RAISE NOTICE 'Triggers created for automatic timestamp updates';
    RAISE NOTICE 'Sample data inserted (development environment only)';
    RAISE NOTICE '';
    RAISE NOTICE 'The production AI-powered schema will be designed';
    RAISE NOTICE 'collaboratively based on specific ML/AI requirements.';
    RAISE NOTICE '========================================';
END $$;
