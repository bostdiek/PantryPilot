"""Integration tests for the meal plans API endpoints.

These tests run against an in-memory SQLite database using an override for
the `get_db` dependency, so they don't require Postgres or Alembic.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import date

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from api.v1.recipes import create_recipe  # type: ignore
from dependencies.db import get_db
from main import app
from models.base import Base
from models.meal_history import Meal
from models.users import User
from schemas.recipes import RecipeCategory, RecipeCreate, RecipeDifficulty


@pytest_asyncio.fixture
async def mealplans_client() -> AsyncIterator[AsyncClient]:
    """Async client wired to the FastAPI app using an in-memory SQLite DB.

    We override the app's `get_db` dependency to yield sessions from a temporary
    SQLite database and create all tables up-front for the test session.
    """
    # Create an in-memory SQLite async engine
    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        poolclass=StaticPool,
    )

    # Create only the tables we need for meal plan tests.
    # Important: create a minimal `recipe_names` table first to satisfy the
    # foreign key on Meal.recipe_id without importing the Postgres ARRAY model.
    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS recipe_names (id BLOB PRIMARY KEY)"
        )
        # Now create users and meal_history via ORM metadata
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=[User.__table__, Meal.__table__]
            )
        )

    # Session factory for the tests
    SessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async def _override_get_db():
        async with SessionLocal() as session:
            yield session

    # Apply the dependency override only for this client lifetime
    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        try:
            yield client
        finally:
            app.dependency_overrides.pop(get_db, None)
            await engine.dispose()


@pytest.mark.asyncio
async def test_weekly_plan_empty_returns_7_days(mealplans_client: AsyncClient) -> None:
    # Pick a mid-week start and ensure server snaps to Sunday
    start_str = "2025-01-14"  # Tuesday
    resp = await mealplans_client.get(f"/api/v1/mealplans/weekly?start={start_str}")
    assert resp.status_code == status.HTTP_200_OK
    payload = resp.json()
    assert payload["success"] is True

    data = payload["data"]
    # Week should start on the previous Sunday (2025-01-12)
    assert data["week_start_date"] == "2025-01-12"
    assert len(data["days"]) == 7
    # All days empty initially
    assert all(len(day["entries"]) == 0 for day in data["days"])


@pytest.mark.asyncio
async def test_put_weekly_and_get_roundtrip_with_ordering(
    mealplans_client: AsyncClient,
) -> None:
    # Define a known week start (Sunday)
    week_start = date(2025, 1, 12)
    # Two entries on Monday; one without explicit order_index should be appended
    payload = [
        {
            "planned_for_date": week_start.isoformat(),
            "meal_type": "dinner",
            "recipe_id": None,
            "is_leftover": False,
            "is_eating_out": False,
            "notes": "Sun #1",
            "order_index": 0,
        },
        {
            "planned_for_date": (week_start.replace(day=13)).isoformat(),  # Monday
            "meal_type": "dinner",
            "recipe_id": None,
            "is_leftover": False,
            "is_eating_out": False,
            "notes": "Mon #1",
            "order_index": 0,
        },
        {
            "planned_for_date": (week_start.replace(day=13)).isoformat(),
            "meal_type": "dinner",
            "recipe_id": None,
            "is_leftover": True,
            "is_eating_out": False,
            "notes": "Mon #2 (leftover)",
            "order_index": None,
        },
    ]

    resp_put = await mealplans_client.put(
        f"/api/v1/mealplans/weekly?start={week_start.isoformat()}", json=payload
    )
    assert resp_put.status_code == status.HTTP_200_OK
    assert resp_put.json()["success"] is True

    # Now fetch the week and verify ordering within Monday
    resp = await mealplans_client.get(f"/api/v1/mealplans/weekly?start={week_start}")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert data["week_start_date"] == week_start.isoformat()

    # Find Monday
    monday = next(d for d in data["days"] if d["date"] == "2025-01-13")
    entries = monday["entries"]
    assert len(entries) == 2
    # First should be order_index 0, second should be 1
    assert [e["order_index"] for e in entries] == [0, 1]
    assert entries[1]["is_leftover"] is True


@pytest.mark.asyncio
async def test_meal_crud_and_cooked_flow(mealplans_client: AsyncClient) -> None:
    # Create a meal entry (leftover, no recipe)
    payload = {
        "planned_for_date": "2025-01-14",
        "meal_type": "dinner",
        "recipe_id": None,
        "is_leftover": True,
        "is_eating_out": False,
        "notes": "Initial",
        "order_index": None,
    }
    resp_create = await mealplans_client.post("/api/v1/meals/", json=payload)
    assert resp_create.status_code == status.HTTP_200_OK
    created = resp_create.json()["data"]
    meal_id = created["id"]

    # Patch notes and set explicit order_index
    patch = {"notes": "Updated", "order_index": 3}
    resp_patch = await mealplans_client.patch(f"/api/v1/meals/{meal_id}", json=patch)
    assert resp_patch.status_code == status.HTTP_200_OK
    updated = resp_patch.json()["data"]
    assert updated["notes"] == "Updated"
    assert updated["order_index"] == 3

    # Mark cooked
    resp_cooked = await mealplans_client.post(
        f"/api/v1/meals/{meal_id}/cooked", json={}
    )
    assert resp_cooked.status_code == status.HTTP_200_OK
    cooked = resp_cooked.json()["data"]
    assert cooked["was_cooked"] is True
    assert cooked["cooked_at"] is not None

    # Delete the meal
    resp_del = await mealplans_client.delete(f"/api/v1/meals/{meal_id}")
    assert resp_del.status_code == status.HTTP_200_OK
    assert resp_del.json()["data"]["id"] == meal_id


@pytest.mark.asyncio
async def test_put_weekly_rejects_out_of_week_entry(
    mealplans_client: AsyncClient,
) -> None:
    week_start = date(2025, 1, 12)  # Sunday
    # This entry is outside the week (next Sunday)
    bad_payload = [
        {
            "planned_for_date": "2025-01-19",
            "meal_type": "dinner",
            "recipe_id": None,
            "is_leftover": False,
            "is_eating_out": False,
            "notes": "Out of range",
            "order_index": 0,
        }
    ]
    resp = await mealplans_client.put(
        f"/api/v1/mealplans/weekly?start={week_start.isoformat()}", json=bad_payload
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    data = resp.json()
    assert data["detail"] == "All entries must be within the specified week"


@pytest.mark.asyncio
async def test_move_entry_across_days_via_patch(mealplans_client: AsyncClient) -> None:
    # Create on Monday
    create_payload = {
        "planned_for_date": "2025-01-13",
        "meal_type": "dinner",
        "recipe_id": None,
        "is_leftover": False,
        "is_eating_out": False,
        "notes": "Move me",
        "order_index": 0,
    }
    resp_create = await mealplans_client.post("/api/v1/meals/", json=create_payload)
    assert resp_create.status_code == status.HTTP_200_OK
    meal_id = resp_create.json()["data"]["id"]

    # Move to Wednesday with order_index 0
    patch = {"planned_for_date": "2025-01-15", "order_index": 0}
    resp_patch = await mealplans_client.patch(f"/api/v1/meals/{meal_id}", json=patch)
    assert resp_patch.status_code == status.HTTP_200_OK

    # Verify via weekly GET
    resp = await mealplans_client.get("/api/v1/mealplans/weekly?start=2025-01-12")
    assert resp.status_code == status.HTTP_200_OK
    week = resp.json()["data"]
    monday = next(d for d in week["days"] if d["date"] == "2025-01-13")
    weds = next(d for d in week["days"] if d["date"] == "2025-01-15")
    assert len(monday["entries"]) == 0
    assert len(weds["entries"]) == 1
    assert weds["entries"][0]["id"] == meal_id
    assert weds["entries"][0]["order_index"] == 0


# Helper fixture that returns both an AsyncClient and a recipe seeding helper
class _MealplansEnv:
    def __init__(self, client: AsyncClient, engine: AsyncEngine):
        self.client = client
        self._engine = engine

    async def seed_recipe(self, recipe_id: uuid.UUID) -> None:
        async with self._engine.begin() as conn:
            await conn.exec_driver_sql(
                "INSERT OR IGNORE INTO recipe_names (id) VALUES (?)",
                (recipe_id.bytes,),
            )


@pytest_asyncio.fixture
async def mealplans_env() -> AsyncIterator[_MealplansEnv]:
    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS recipe_names (id BLOB PRIMARY KEY)"
        )
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=[User.__table__, Meal.__table__]
            )
        )
    SessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async def _override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        try:
            yield _MealplansEnv(client, engine)
        finally:
            app.dependency_overrides.pop(get_db, None)
            await engine.dispose()


@pytest.mark.asyncio
async def test_create_recipe_then_plan_it(mealplans_env: _MealplansEnv) -> None:  # noqa: C901
    recipe_id = await _create_recipe_via_fake_db()

    # Seed that recipe ID into the SQLite test DB and plan it
    await mealplans_env.seed_recipe(recipe_id)
    plan_payload = {
        "planned_for_date": "2025-01-14",
        "meal_type": "dinner",
        "recipe_id": str(recipe_id),
        "is_leftover": False,
        "is_eating_out": False,
        "notes": "use recipe",
        "order_index": None,
    }
    # Call the route function directly to avoid dependency injection plumbing.
    from api.v1.mealplans import create_meal_entry  # type: ignore
    from schemas.mealplans import MealEntryIn

    SessionLocal = async_sessionmaker(
        mealplans_env._engine, expire_on_commit=False, class_=AsyncSession
    )
    async with SessionLocal() as session:
        entry = MealEntryIn(**plan_payload)
        api_resp = await create_meal_entry(entry, session)  # type: ignore[arg-type]
        assert api_resp.success is True
        created = api_resp.data
        assert created.recipe_id == recipe_id
    # Verify in weekly view
    resp_week = await mealplans_env.client.get(
        "/api/v1/mealplans/weekly?start=2025-01-12"
    )
    assert resp_week.status_code == status.HTTP_200_OK
    week = resp_week.json()["data"]
    tuesday = next(d for d in week["days"] if d["date"] == "2025-01-14")
    assert any(e["recipe_id"] == str(recipe_id) for e in tuesday["entries"])


async def _create_recipe_via_fake_db() -> uuid.UUID:  # noqa: C901
    """Create a recipe using a temporary fake DB override and return its ID."""

    class _FakeResult:
        def scalars(self):
            return self

        def first(self):
            return None

    class _FakeSession:
        def add(self, _obj):
            return None

        async def flush(self):
            return None

        async def execute(self, _stmt):
            return _FakeResult()

        async def commit(self):
            return None

        async def rollback(self):
            return None

        async def close(self):
            return None

        async def refresh(self, _obj):
            return None

    # Build the Pydantic payload
    payload = RecipeCreate(
        title="Planner Test Recipe",
        description="desc",
        prep_time_minutes=5,
        cook_time_minutes=10,
        serving_min=1,
        serving_max=2,
        instructions=["step1"],
        difficulty=RecipeDifficulty.MEDIUM,
        category=RecipeCategory.DINNER,
        ethnicity="",
        ingredients=[
            {
                "name": "Water",
                "quantity_value": 1,
                "quantity_unit": "cup",
                "is_optional": False,
            }
        ],
    )

    fake = _FakeSession()
    try:
        api_resp = await create_recipe(payload, fake)  # type: ignore[arg-type]
        assert api_resp.success is True
        return uuid.UUID(str(api_resp.data.id))
    finally:
        await fake.close()


@pytest.mark.asyncio
async def test_move_multiple_to_same_day_stable_order(
    mealplans_client: AsyncClient,
) -> None:
    # Create A on Monday
    a_resp = await mealplans_client.post(
        "/api/v1/meals/",
        json={
            "planned_for_date": "2025-01-13",
            "meal_type": "dinner",
            "recipe_id": None,
            "is_leftover": False,
            "is_eating_out": False,
            "notes": "A",
            "order_index": 0,
        },
    )
    assert a_resp.status_code == status.HTTP_200_OK
    a_id = a_resp.json()["data"]["id"]

    # Create B on Tuesday
    b_resp = await mealplans_client.post(
        "/api/v1/meals/",
        json={
            "planned_for_date": "2025-01-14",
            "meal_type": "dinner",
            "recipe_id": None,
            "is_leftover": False,
            "is_eating_out": False,
            "notes": "B",
            "order_index": 0,
        },
    )
    assert b_resp.status_code == status.HTTP_200_OK
    b_id = b_resp.json()["data"]["id"]

    # Create C on Wednesday
    c_resp = await mealplans_client.post(
        "/api/v1/meals/",
        json={
            "planned_for_date": "2025-01-15",
            "meal_type": "dinner",
            "recipe_id": None,
            "is_leftover": False,
            "is_eating_out": False,
            "notes": "C",
            "order_index": 0,
        },
    )
    assert c_resp.status_code == status.HTTP_200_OK
    c_id = c_resp.json()["data"]["id"]

    # Move B then C to Monday with explicit indices to preserve stable order
    patch_b = {"planned_for_date": "2025-01-13", "order_index": 1}
    patch_c = {"planned_for_date": "2025-01-13", "order_index": 2}
    r1 = await mealplans_client.patch(f"/api/v1/meals/{b_id}", json=patch_b)
    r2 = await mealplans_client.patch(f"/api/v1/meals/{c_id}", json=patch_c)
    assert r1.status_code == r2.status_code == status.HTTP_200_OK

    # Verify order A,B,C by order_index 0,1,2
    resp = await mealplans_client.get("/api/v1/mealplans/weekly?start=2025-01-12")
    assert resp.status_code == status.HTTP_200_OK
    week = resp.json()["data"]
    monday = next(d for d in week["days"] if d["date"] == "2025-01-13")
    ids_in_order = [e["id"] for e in monday["entries"]]
    orders = [e["order_index"] for e in monday["entries"]]
    assert ids_in_order == [a_id, b_id, c_id]
    assert orders == [0, 1, 2]
