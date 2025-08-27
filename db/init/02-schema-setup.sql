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

-- Ingredient names table (basic structure)
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
-- NOTE (schema): `instructions` is stored as a list of steps (TEXT array).
-- If you prefer richer step metadata (timings, images, tips), consider JSONB.
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
    instructions TEXT[],
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
    quantity_value NUMERIC,
    quantity_unit VARCHAR(64),
    prep JSONB DEFAULT '{}'::jsonb,
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
    recipe_id UUID NOT NULL REFERENCES recipe_names(id) ON DELETE CASCADE,
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
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Ingredient name indexes
CREATE INDEX IF NOT EXISTS idx_ingredient_names_name ON ingredient_names(ingredient_name);
CREATE INDEX IF NOT EXISTS idx_ingredient_names_name_trgm ON ingredient_names USING gin (ingredient_name gin_trgm_ops);

-- Recipe name indexes
CREATE INDEX IF NOT EXISTS idx_recipe_names_name ON recipe_names(name);
CREATE INDEX IF NOT EXISTS idx_recipe_names_name_trgm ON recipe_names USING gin (name gin_trgm_ops);

-- Recipe ingredients indexes
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_ingredient_id ON recipe_ingredients(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_quantity_value ON recipe_ingredients(quantity_value);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_prep_gin ON recipe_ingredients USING GIN (prep);

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

CREATE TRIGGER update_ingredient_names_updated_at
    BEFORE UPDATE ON ingredient_names
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recipe_names_updated_at
    BEFORE UPDATE ON recipe_names
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recipe_ingredients_updated_at
    BEFORE UPDATE ON recipe_ingredients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_meal_history_updated_at
    BEFORE UPDATE ON meal_history
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
        INSERT INTO users (email, username, hashed_password, first_name, last_name)
        VALUES (
            'demo@pantrypilot.dev',
            'demo',
            '$2b$12$SecureHashForDemoAccountOnlyNotForProd.Development.Only',
            'Demo',
            'User'
        ) ON CONFLICT (email) DO NOTHING;

        -- Insert sample ingredient names
        INSERT INTO ingredient_names (ingredient_name)
        SELECT unnest(ARRAY['Flour', 'Sugar', 'Eggs', 'Milk', 'Chicken Breast', 'Tomatoes', 'Onions', 'Garlic'])
        ON CONFLICT DO NOTHING;

        -- Insert a sample recipe and link a couple of ingredients
        WITH r AS (
            -- instructions as a text array (one entry per step)
            INSERT INTO recipe_names (name, instructions, user_notes)
            VALUES ('Simple Omelette', ARRAY['Beat eggs, cook in butter, fold and serve.'], 'Basic demo recipe')
            RETURNING id
        )
        INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity_value, quantity_unit, prep)
        SELECT r.id,
               i.id,
               x.qty::numeric,
               x.unit,
               CASE i.ingredient_name
                   WHEN 'Eggs' THEN '{"size_descriptor": "large", "size_unit": "count"}'::jsonb
                   WHEN 'Milk' THEN '{"method": "none"}'::jsonb
                   ELSE '{}'::jsonb
               END
        FROM r
        JOIN ingredient_names i ON i.ingredient_name = ANY(ARRAY['Eggs','Milk'])
        JOIN (
            SELECT unnest(ARRAY['2','1']) AS qty, unnest(ARRAY['count','cup']) AS unit
        ) x ON TRUE
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
    RAISE NOTICE 'Tables created: users, ingredient_names, recipe_names, recipe_ingredients, meal_history';
    RAISE NOTICE 'Indexes created for optimal query performance';
    RAISE NOTICE 'Triggers created for automatic timestamp updates';
    RAISE NOTICE 'Sample data inserted (development environment only)';
    RAISE NOTICE '';
    RAISE NOTICE 'The production AI-powered schema will be designed';
    RAISE NOTICE 'collaboratively based on specific ML/AI requirements.';
    RAISE NOTICE '========================================';
END $$;
