from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, asc, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import check_resource_access, check_resource_write_access, get_current_user
from dependencies.db import get_db
from models.meal_history import Meal
from models.users import User
from schemas.api import ApiResponse
from schemas.mealplans import (
    DayPlanOut,
    MarkCookedIn,
    MealEntryIn,
    MealEntryOut,
    MealEntryPatch,
    WeeklyMealPlanOut,
)


router = APIRouter(prefix="/mealplans", tags=["mealplans"])
meals_router = APIRouter(prefix="/meals", tags=["meals"])


def _sunday_start(d: date) -> date:
    # Ensure week starts Sunday
    # Python weekday(): Mon=0..Sun=6; want Sun=0 => offset = (weekday+1) % 7
    offset = (d.weekday() + 1) % 7
    return d - timedelta(days=offset)


async def _get_or_create_demo_user(db: AsyncSession) -> User:
    """Temporary helper to provide a user in non-auth dev environments.

    If a user exists, return the first one. Otherwise create a demo user.
    """
    result = await db.execute(select(User).limit(1))
    user = result.scalars().first()
    if user:
        return user
    # Create a minimal demo user
    user = User(
        username="demo",
        email="demo@pantrypilot.local",
        hashed_password="demo",
        first_name="Demo",
        last_name="User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _meal_to_out(m: Meal) -> MealEntryOut:
    # Cast SQLAlchemy-instrumented attributes to runtime types for mypy
    return MealEntryOut(
        id=cast(UUID, m.id),
        planned_for_date=cast(date, m.planned_for_date),
        recipe_id=cast(UUID | None, m.recipe_id),
        meal_type=cast(Literal["dinner"], (m.meal_type or "dinner")),
        is_leftover=bool(m.is_leftover),
        is_eating_out=bool(m.is_eating_out),
        notes=cast(str | None, m.notes),
        order_index=cast(int, m.order_index),
        was_cooked=bool(m.was_cooked),
        cooked_at=cast(datetime | None, m.cooked_at),
    )


def _apply_meal_patch(meal: Meal, patch: MealEntryPatch) -> None:
    """Apply a partial update to a Meal entity in-place."""
    scalar_updates = (
        ("planned_for_date", patch.planned_for_date),
        ("recipe_id", patch.recipe_id),
        ("meal_type", patch.meal_type),
        ("is_leftover", patch.is_leftover),
        ("is_eating_out", patch.is_eating_out),
        ("notes", patch.notes),
        ("order_index", patch.order_index),
    )
    for attr, val in scalar_updates:
        if val is not None:
            setattr(meal, attr, val)

    _apply_cooked_patch(meal, patch)


def _apply_cooked_patch(meal: Meal, patch: MealEntryPatch) -> None:
    # Cooked state updates — use cast(Any, meal) for write assignments to SA columns
    m_any = cast(Any, meal)
    if patch.cooked_at is not None:
        m_any.cooked_at = patch.cooked_at
        m_any.was_cooked = True
    if patch.was_cooked is not None:
        m_any.was_cooked = patch.was_cooked
        current_cooked_at = cast(datetime | None, meal.cooked_at)
        if patch.was_cooked and current_cooked_at is None:
            m_any.cooked_at = datetime.now(UTC)
        if patch.was_cooked is False:
            m_any.cooked_at = None


@router.get(
    "/weekly",
    summary="Get weekly meal plan",
    response_model=ApiResponse[WeeklyMealPlanOut],
)
async def get_weekly_meal_plan(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    start: date | None = None,
) -> ApiResponse[WeeklyMealPlanOut]:
    """Return the weekly meal plan for the authenticated user."""
    start_date = _sunday_start(start or date.today())
    end_date = start_date + timedelta(days=7)

    stmt = (
        select(Meal)
        .where(
            and_(
                Meal.user_id == current_user.id,
                Meal.planned_for_date >= start_date,
                Meal.planned_for_date < end_date,
            )
        )
        .order_by(asc(Meal.planned_for_date), asc(Meal.order_index), asc(Meal.id))
    )
    result = await db.execute(stmt)
    meals: list[Meal] = list(result.scalars().all())

    # Bucket meals by day
    by_date: dict[date, list[MealEntryOut]] = {}
    for m in meals:
        d_planned = cast(date, m.planned_for_date)
        by_date.setdefault(d_planned, []).append(_meal_to_out(m))

    days: list[DayPlanOut] = []
    for i in range(7):
        d = start_date + timedelta(days=i)
        day_label = cast(
            Literal[
                "Sunday",
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
            ],
            d.strftime("%A"),
        )
        days.append(
            DayPlanOut(
                day_of_week=day_label,
                date=d,
                entries=by_date.get(d, []),
            )
        )

    return ApiResponse(
        success=True,
        data=WeeklyMealPlanOut(week_start_date=start_date, days=days),
    )


@router.put(
    "/weekly",
    summary="Replace weekly meal plan",
    response_model=ApiResponse[WeeklyMealPlanOut],
)
async def replace_weekly_plan(
    payload: list[MealEntryIn],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    start: date | None = None,
) -> ApiResponse[WeeklyMealPlanOut]:
    """Replace the given week's entries with provided entries for the user.

    Clears existing entries in the week range, then inserts the new ones.
    """
    start_date = _sunday_start(start or date.today())
    end_date = start_date + timedelta(days=7)

    # Validate all entries are within the target week
    for e in payload:
        if e.planned_for_date < start_date or e.planned_for_date >= end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All entries must be within the specified week",
            )

    # Delete existing entries for the week
    await db.execute(
        delete(Meal).where(
            and_(
                Meal.user_id == current_user.id,
                Meal.planned_for_date >= start_date,
                Meal.planned_for_date < end_date,
            )
        )
    )

    # Insert new entries; compute per-day order_index when missing
    order_track: dict[date, int] = {}
    for e in payload:
        idx = e.order_index
        if idx is None:
            idx = order_track.get(e.planned_for_date, -1) + 1
        order_track[e.planned_for_date] = idx

        meal = Meal(
            user_id=current_user.id,
            recipe_id=e.recipe_id,
            planned_for_date=e.planned_for_date,
            meal_type=e.meal_type,
            order_index=idx,
            is_leftover=e.is_leftover,
            is_eating_out=e.is_eating_out,
            notes=e.notes,
            was_cooked=False,
            cooked_at=None,
        )
        db.add(meal)

    await db.commit()

    # Return the newly built week
    return await get_weekly_meal_plan(start=start_date, db=db, current_user=current_user)


@meals_router.post(
    "/",
    summary="Create a meal entry",
    response_model=ApiResponse[MealEntryOut],
)
async def create_meal_entry(
    entry: MealEntryIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[MealEntryOut]:
    """Create a new meal plan entry for the authenticated user."""

    # Determine next order_index if not provided
    idx = entry.order_index
    if idx is None:
        stmt = select(func.max(Meal.order_index)).where(
            and_(
                Meal.user_id == current_user.id,
                Meal.planned_for_date == entry.planned_for_date,
            )
        )
        result = await db.execute(stmt)
        max_idx = result.scalar() or -1
        idx = int(max_idx) + 1

    meal = Meal(
        user_id=current_user.id,
        recipe_id=entry.recipe_id,
        planned_for_date=entry.planned_for_date,
        meal_type=entry.meal_type,
        order_index=idx,
        is_leftover=entry.is_leftover,
        is_eating_out=entry.is_eating_out,
        notes=entry.notes,
        was_cooked=False,
        cooked_at=None,
    )
    db.add(meal)
    await db.commit()
    await db.refresh(meal)
    return ApiResponse(success=True, data=_meal_to_out(meal))


@meals_router.patch(
    "/{meal_id}",
    summary="Update a meal entry",
    response_model=ApiResponse[MealEntryOut],
)
async def update_meal_entry(
    meal_id: UUID,
    patch: MealEntryPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[MealEntryOut]:
    """Update an existing meal plan entry (basic field updates)."""
    result = await db.execute(select(Meal).where(Meal.id == meal_id))
    meal = result.scalars().first()
    
    # Check ownership
    meal = check_resource_write_access(
        meal,
        current_user,
        not_found_message="Meal entry not found",
        forbidden_message="Not allowed to modify this meal entry"
    )
    _apply_meal_patch(meal, patch)

    await db.commit()
    await db.refresh(meal)
    return ApiResponse(success=True, data=_meal_to_out(meal))


@meals_router.delete(
    "/{meal_id}",
    summary="Delete a meal entry",
    response_model=ApiResponse[dict[str, Any]],
)
async def delete_meal_entry(
    meal_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[dict[str, Any]]:
    """Delete a meal entry."""
    result = await db.execute(select(Meal).where(Meal.id == meal_id))
    meal = result.scalars().first()
    
    # Check ownership before deletion
    meal = check_resource_write_access(
        meal,
        current_user,
        not_found_message="Meal entry not found",
        forbidden_message="Not allowed to delete this meal entry"
    )
    
    await db.execute(delete(Meal).where(Meal.id == meal_id))
    await db.commit()
    return ApiResponse(success=True, data={"id": str(meal_id)})


@meals_router.post(
    "/{meal_id}/cooked",
    summary="Mark a meal entry as cooked",
    response_model=ApiResponse[MealEntryOut],
)
async def mark_meal_cooked(
    meal_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    payload: MarkCookedIn | None = None,
) -> ApiResponse[MealEntryOut]:
    """Mark a meal as cooked (sets was_cooked and cooked_at)."""
    result = await db.execute(select(Meal).where(Meal.id == meal_id))
    meal = result.scalars().first()
    
    # Check ownership
    meal = check_resource_write_access(
        meal,
        current_user,
        not_found_message="Meal entry not found",
        forbidden_message="Not allowed to modify this meal entry"
    )
    cooked_at: datetime | None = payload.cooked_at if payload else None
    m_any = cast(Any, meal)
    m_any.was_cooked = True
    m_any.cooked_at = cooked_at or datetime.now(UTC)
    await db.commit()
    await db.refresh(meal)
    return ApiResponse(success=True, data=_meal_to_out(meal))
