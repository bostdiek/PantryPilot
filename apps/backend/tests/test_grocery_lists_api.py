"""Tests for grocery list API functionality."""

from collections.abc import AsyncIterator
from datetime import date, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from dependencies.auth import get_current_user
from dependencies.db import get_db
from main import app
from models.base import Base
from models.ingredient_names import Ingredient
from models.meal_history import Meal
from models.recipe_ingredients import RecipeIngredient
from models.recipes_names import Recipe
from models.users import User


@pytest_asyncio.fixture
async def grocery_client() -> AsyncIterator[tuple[AsyncClient, AsyncSession]]:
    """Async client wired to FastAPI app using in-memory SQLite for grocery tests."""
    # Create an in-memory SQLite async engine
    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        poolclass=StaticPool,
    )

    # Create all necessary tables for grocery list tests
    async with engine.begin() as conn:
        # Create minimal recipe_names table without PostgreSQL ARRAY type
        await conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS recipe_names (
                id BLOB PRIMARY KEY,
                user_id BLOB,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                prep_time_minutes INTEGER,
                cook_time_minutes INTEGER,
                total_time_minutes INTEGER,
                serving_min INTEGER,
                serving_max INTEGER,
                ethnicity VARCHAR(255),
                difficulty VARCHAR(50),
                course_type VARCHAR(255),
                oven_temperature_f INTEGER,
                instructions TEXT,
                user_notes TEXT,
                ai_summary TEXT,
                link_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create recipe_ingredients table without PostgreSQL JSONB type
        await conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS recipe_ingredients (
                id BLOB PRIMARY KEY,
                recipe_id BLOB NOT NULL,
                ingredient_id BLOB NOT NULL,
                quantity_value NUMERIC,
                quantity_unit VARCHAR(64),
                prep TEXT DEFAULT '{}',
                is_optional BOOLEAN DEFAULT 0,
                user_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create other tables normally
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=[User.__table__, Ingredient.__table__, Meal.__table__]
            )
        )

    # Session factory for the tests
    SessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async def _override_get_db():
        async with SessionLocal() as session:
            yield session

    # Auth override: always return first user (create one if none)
    async def _override_get_current_user():
        async with SessionLocal() as session:
            result = await session.execute(select(User).limit(1))
            user = result.scalars().first()
            if not user:
                demo = User(
                    username="demo",
                    email="demo@tests.local",
                    hashed_password="x",
                )
                session.add(demo)
                await session.commit()
                await session.refresh(demo)
                return demo
            return user

    # Override dependencies
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    # Create and yield the client with session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        async with SessionLocal() as session:
            yield client, session

    # Clean up overrides
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    await engine.dispose()


class TestGroceryListAPI:
    """Test cases for grocery list API endpoints."""

    @pytest.mark.asyncio
    async def test_generate_grocery_list_success(self, grocery_client):
        """Test successful grocery list generation with valid data."""
        client, session = grocery_client

        # Create demo user
        demo_user = User(
            id=uuid4(),
            username="demo",
            email="demo@tests.local",
            hashed_password="x",
        )
        session.add(demo_user)
        await session.commit()

        # Create test data: recipe, ingredients, meal history
        recipe = Recipe(
            id=uuid4(),
            user_id=demo_user.id,
            name="Test Recipe",
            prep_time_minutes=15,
            cook_time_minutes=30,
        )
        session.add(recipe)

        # Create ingredients
        ingredient1 = Ingredient(
            id=uuid4(),
            user_id=demo_user.id,
            ingredient_name="Tomatoes",
        )
        ingredient2 = Ingredient(
            id=uuid4(),
            user_id=demo_user.id,
            ingredient_name="Onions",
        )
        session.add_all([ingredient1, ingredient2])

        # Create recipe ingredients
        recipe_ingredient1 = RecipeIngredient(
            id=uuid4(),
            recipe_id=recipe.id,
            ingredient_id=ingredient1.id,
            quantity_value=2.0,
            quantity_unit="cups",
            is_optional=False,
        )
        recipe_ingredient2 = RecipeIngredient(
            id=uuid4(),
            recipe_id=recipe.id,
            ingredient_id=ingredient2.id,
            quantity_value=1.0,
            quantity_unit="pieces",
            is_optional=False,
        )
        session.add_all([recipe_ingredient1, recipe_ingredient2])

        # Create meal history
        today = date.today()
        meal = Meal(
            id=uuid4(),
            user_id=demo_user.id,
            recipe_id=recipe.id,
            planned_for_date=today,
            meal_type="dinner",
            is_leftover=False,
            is_eating_out=False,
        )
        session.add(meal)
        await session.commit()

        # Test the API endpoint
        response = await client.post(
            "/api/v1/grocery-lists",
            json={
                "start_date": today.isoformat(),
                "end_date": today.isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        grocery_list = data["data"]

        assert grocery_list["start_date"] == today.isoformat()
        assert grocery_list["end_date"] == today.isoformat()
        assert grocery_list["total_meals"] == 1
        assert len(grocery_list["ingredients"]) == 2

        # Check ingredient details
        ingredients = grocery_list["ingredients"]
        ingredient_names = [ing["name"] for ing in ingredients]
        assert "Tomatoes" in ingredient_names
        assert "Onions" in ingredient_names

        # Check specific ingredient details
        tomato_ingredient = next(
            ing for ing in ingredients if ing["name"] == "Tomatoes"
        )
        assert tomato_ingredient["quantity_value"] == 2.0
        assert tomato_ingredient["quantity_unit"] == "cups"
        assert "Test Recipe" in tomato_ingredient["recipes"]

    @pytest.mark.asyncio
    async def test_generate_grocery_list_empty_date_range(self, grocery_client):
        """Test grocery list generation with no meals in date range."""
        client, session = grocery_client
        future_date = date.today() + timedelta(days=30)

        response = await client.post(
            "/api/v1/grocery-lists",
            json={
                "start_date": future_date.isoformat(),
                "end_date": future_date.isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        grocery_list = data["data"]

        assert grocery_list["total_meals"] == 0
        assert len(grocery_list["ingredients"]) == 0

    @pytest.mark.asyncio
    async def test_generate_grocery_list_invalid_date_range(self, grocery_client):
        """Test grocery list generation with invalid date range."""
        client, _ = grocery_client
        today = date.today()
        yesterday = today - timedelta(days=1)

        response = await client.post(
            "/api/v1/grocery-lists",
            json={
                "start_date": today.isoformat(),
                "end_date": yesterday.isoformat(),  # End before start
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "End date must be on or after start date" in data["detail"]

    @pytest.mark.asyncio
    async def test_generate_grocery_list_unauthorized(self):
        """Test that grocery list generation requires authentication."""
        today = date.today()

        # Create client without auth override
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/api/v1/grocery-lists",
                json={
                    "start_date": today.isoformat(),
                    "end_date": today.isoformat(),
                },
            )

            assert response.status_code == 401
