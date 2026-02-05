"""Seed database with persona data for synthetic training data generation.

This module provides functions to seed the dev database with synthetic users
and their associated data (recipes, meal plans, preferences) for each persona
defined in the training module.

Usage:
    # From apps/backend directory with database running:
    PYTHONPATH=./src uv run python -m training.seed_database
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.security import get_password_hash
from models.base import Base
from models.ingredient_names import Ingredient
from models.meal_history import Meal
from models.recipes_names import Recipe
from models.user_preferences import UserPreferences
from models.users import User
from training.personas import PERSONAS, PersonaProfile, RecipeData


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Synthetic user password (used for authentication in training data generation)
SYNTHETIC_PASSWORD = "SyntheticUser2026!"  # noqa: S105  # pragma: allowlist secret


def _load_env_files() -> None:
    """Load environment files for database connection."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    for fname in (".env", ".env.dev"):
        for p in Path(__file__).resolve().parents:
            candidate = p / fname
            if candidate.exists():
                load_dotenv(dotenv_path=candidate, override=False)
                return


def _normalize_asyncpg_url(url: str) -> str:
    """Convert a postgres URL to asyncpg format and fix SSL parameters.

    asyncpg requires 'ssl=require' instead of 'sslmode=require'.
    """
    # Normalize to async driver if a plain postgres URL is provided
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    elif url.startswith("postgresql+psycopg2://") or url.startswith(
        "postgresql+psycopg://"
    ):
        url = "postgresql+asyncpg://" + url.split("://", 1)[1]

    # asyncpg doesn't accept 'sslmode' parameter, convert to 'ssl'
    url = url.replace("sslmode=require", "ssl=require")
    return url


def _get_database_url() -> str:
    """Build database URL for execution.

    Supports:
    1. DATABASE_URL environment variable (for cloud/Azure PostgreSQL)
    2. POSTGRES_* variables with localhost (for local development)
    """
    _load_env_files()

    # Check for explicit DATABASE_URL first (cloud database)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Normalize for asyncpg
        normalized = _normalize_asyncpg_url(database_url)
        # Replace 'db' hostname with localhost if running outside Docker
        if "@db:" in normalized or "@db/" in normalized:
            normalized = normalized.replace("@db:", "@localhost:").replace(
                "@db/", "@localhost/"
            )
        logger.info("Using DATABASE_URL (cloud or explicit configuration)")
        return normalized

    # Fall back to constructing from POSTGRES_* variables (local dev)
    user = os.getenv("POSTGRES_USER", "pantrypilot_dev")
    password = os.getenv("POSTGRES_PASSWORD", "dev_password_123")
    db = os.getenv("POSTGRES_DB", "pantrypilot_dev")
    port = os.getenv("POSTGRES_PORT", "5432")
    host = os.getenv("POSTGRES_HOST", "localhost")

    # For local execution outside Docker, use localhost
    if host == "db":
        host = "localhost"

    logger.info("Using local database at %s:%s", host, port)
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


async def create_persona_user(
    db: AsyncSession,
    persona_name: str,
    persona: PersonaProfile,
) -> User:
    """Create a synthetic user for a persona.

    Args:
        db: Database session
        persona_name: Name of the persona (e.g., "veggie_val")
        persona: PersonaProfile with user data

    Returns:
        Created User object with ID populated
    """
    # Generate deterministic email from persona name
    email = f"{persona['user_id']}@pantrypilot.synthetic"
    username = persona["user_id"]  # e.g., "synthetic-veggie-val"

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(SYNTHETIC_PASSWORD),
        is_verified=True,  # Skip email verification for synthetic users
        first_name=_extract_first_name(persona_name),
        last_name="(Synthetic)",
    )
    db.add(user)
    await db.flush()  # Get user ID assigned

    logger.info("Created synthetic user: %s (ID: %s)", email, user.id)
    return user


async def create_persona_preferences(
    db: AsyncSession,
    user: User,
    persona: PersonaProfile,
) -> UserPreferences:
    """Create user preferences from persona profile.

    Args:
        db: Database session
        user: User to associate preferences with
        persona: PersonaProfile with preference data

    Returns:
        Created UserPreferences object
    """
    prefs = persona["preferences"]
    location = prefs["location"]

    preferences = UserPreferences(
        user_id=user.id,
        # Dietary settings
        dietary_restrictions=prefs.get("dietary_restrictions", []),
        allergies=[],  # Not specified in personas, default empty
        preferred_cuisines=prefs.get("cuisine_preferences", []),
        # Family settings
        family_size=prefs.get("household_size", 2),
        default_servings=prefs.get("household_size", 2) * 2,  # 2 servings per person
        # Location for weather tool
        city=location["city"],
        state_or_region=location["state_or_region"],
        postal_code=location["postal_code"],
        country=location["country"][:2] if location["country"] else "US",  # ISO alpha-2
    )
    db.add(preferences)
    await db.flush()

    logger.info(
        "Created preferences for %s: %s, %s",
        user.username,
        location["city"],
        prefs.get("dietary_restrictions", []),
    )
    return preferences


async def create_persona_recipes(
    db: AsyncSession,
    user: User,
    persona: PersonaProfile,
) -> dict[str, Recipe]:
    """Create recipe collection for a persona.

    Args:
        db: Database session
        user: User to own the recipes
        persona: PersonaProfile with recipe data

    Returns:
        Dictionary mapping recipe names to Recipe objects
    """
    recipe_map: dict[str, Recipe] = {}

    for recipe_data in persona["recipes"]:
        # Parse time from tags (e.g., "30min", "60min")
        prep_time, cook_time = _parse_recipe_times(recipe_data.get("tags", []))

        # Calculate total time if both prep and cook times are available
        total_time = None
        if prep_time and cook_time:
            total_time = prep_time + cook_time

        recipe = Recipe(
            user_id=user.id,
            name=recipe_data["name"],
            description=_generate_recipe_description(recipe_data),
            prep_time_minutes=prep_time,
            cook_time_minutes=cook_time,
            total_time_minutes=total_time,
            serving_min=2,
            serving_max=max(4, persona["preferences"].get("household_size", 4)),
            difficulty=_infer_difficulty(recipe_data.get("tags", [])),
            course_type="dinner",
            ethnicity=_infer_ethnicity(recipe_data.get("tags", [])),
            instructions=_generate_placeholder_instructions(recipe_data["name"]),
        )
        db.add(recipe)
        recipe_map[recipe_data["name"]] = recipe

    await db.flush()
    logger.info("Created %d recipes for %s", len(recipe_map), user.username)
    return recipe_map


async def create_persona_ingredients(
    db: AsyncSession,
    user: User,
    persona: PersonaProfile,
) -> list[Ingredient]:
    """Create pantry ingredients for a persona.

    Args:
        db: Database session
        user: User to own the ingredients
        persona: PersonaProfile with pantry data

    Returns:
        List of created Ingredient objects
    """
    ingredients: list[Ingredient] = []

    for item_name in persona["pantry_items"]:
        ingredient = Ingredient(
            user_id=user.id,
            ingredient_name=item_name,
        )
        db.add(ingredient)
        ingredients.append(ingredient)

    await db.flush()
    logger.info("Created %d pantry items for %s", len(ingredients), user.username)
    return ingredients


async def create_persona_meal_history(
    db: AsyncSession,
    user: User,
    persona: PersonaProfile,
    recipe_map: dict[str, Recipe],
) -> list[Meal]:
    """Create meal plan history for a persona.

    Uses relative dates based on current date, so history is always "recent"
    regardless of when the seeding script is run.

    Args:
        db: Database session
        user: User to own the meals
        persona: PersonaProfile with meal history
        recipe_map: Dictionary mapping recipe names to Recipe objects

    Returns:
        List of created Meal objects
    """
    meals: list[Meal] = []
    today = date.today()
    history_entries = persona["meal_plan_history"]

    # Calculate relative dates: distribute meals over the past N days
    # Start from (len(history) - 1) days ago, ending yesterday
    num_entries = len(history_entries)

    for i, entry in enumerate(history_entries):
        # Days ago: first entry is (num_entries - 1) days ago, last is 0 (today-ish)
        # But we want history to end yesterday, so offset by 1
        days_ago = num_entries - i
        meal_date = today - timedelta(days=days_ago)

        # Get recipe ID if it exists in our recipe map
        recipe = recipe_map.get(entry["recipe"])
        recipe_id = recipe.id if recipe else None

        meal = Meal(
            user_id=user.id,
            recipe_id=recipe_id,
            planned_for_date=meal_date,
            meal_type=entry.get("meal", "dinner"),
            was_cooked=True,  # Historical entries assumed cooked
            cooked_at=datetime(
                meal_date.year,
                meal_date.month,
                meal_date.day,
                18,  # 6pm
                0,
            ),
        )
        db.add(meal)
        meals.append(meal)

    await db.flush()
    logger.info("Created %d meal history entries for %s", len(meals), user.username)
    return meals


async def seed_persona(
    db: AsyncSession,
    persona_name: str,
    persona: PersonaProfile,
) -> dict[str, Any]:
    """Seed all data for a single persona.

    Args:
        db: Database session
        persona_name: Name of the persona
        persona: PersonaProfile with all data

    Returns:
        Dictionary with created objects
    """
    logger.info("Seeding persona: %s", persona_name)

    # Create user
    user = await create_persona_user(db, persona_name, persona)

    # Create preferences
    preferences = await create_persona_preferences(db, user, persona)

    # Create recipes
    recipe_map = await create_persona_recipes(db, user, persona)

    # Create ingredients (pantry)
    ingredients = await create_persona_ingredients(db, user, persona)

    # Create meal history (requires recipe_map)
    meals = await create_persona_meal_history(db, user, persona, recipe_map)

    # Commit all changes for this persona
    await db.commit()

    return {
        "user": user,
        "preferences": preferences,
        "recipes": list(recipe_map.values()),
        "ingredients": ingredients,
        "meals": meals,
    }


async def seed_all_personas(db: AsyncSession) -> dict[str, dict[str, Any]]:
    """Seed all personas into the database.

    Args:
        db: Database session

    Returns:
        Dictionary mapping persona names to their seeded data
    """
    results: dict[str, dict[str, Any]] = {}

    for persona_name, persona_data in PERSONAS.items():
        try:
            results[persona_name] = await seed_persona(db, persona_name, persona_data)
        except Exception:
            logger.exception("Failed to seed persona %s", persona_name)
            await db.rollback()
            raise

    return results


async def cleanup_synthetic_users(db: AsyncSession) -> int:
    """Remove all synthetic users and their data.

    This is useful for cleanup before re-seeding.

    Args:
        db: Database session

    Returns:
        Number of users deleted
    """
    from sqlalchemy import delete, select

    # Find all synthetic users
    result = await db.execute(
        select(User).where(User.email.like("%@pantrypilot.synthetic"))
    )
    users = result.scalars().all()
    user_ids = [user.id for user in users]

    if not user_ids:
        logger.info("No synthetic users to delete")
        return 0

    # Delete related records first (in dependency order)
    # Meals reference recipes, so delete meals first
    await db.execute(delete(Meal).where(Meal.user_id.in_(user_ids)))

    # Recipes can be deleted after meals
    await db.execute(delete(Recipe).where(Recipe.user_id.in_(user_ids)))

    # Ingredients (pantry items)
    await db.execute(delete(Ingredient).where(Ingredient.user_id.in_(user_ids)))

    # User preferences
    await db.execute(
        delete(UserPreferences).where(UserPreferences.user_id.in_(user_ids))
    )

    # Finally delete users
    count = 0
    for user in users:
        await db.delete(user)
        count += 1

    await db.commit()
    logger.info("Deleted %d synthetic users and their data", count)
    return count


async def run_seeding(cleanup_first: bool = True) -> dict[str, dict[str, Any]]:
    """Main entry point for seeding.

    Args:
        cleanup_first: Whether to remove existing synthetic users first

    Returns:
        Dictionary with seeding results
    """
    database_url = _get_database_url()
    logger.info("Connecting to database...")

    engine: AsyncEngine = create_async_engine(database_url, echo=False)

    try:
        # Create tables if needed (safe no-op if tables exist)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

        async with async_session() as db:
            if cleanup_first:
                logger.info("Cleaning up existing synthetic users...")
                await cleanup_synthetic_users(db)

            logger.info("Seeding personas...")
            results = await seed_all_personas(db)

            # Summary
            logger.info("\n=== Seeding Complete ===")
            for persona_name, data in results.items():
                logger.info(
                    "  %s: %d recipes, %d meals, %d ingredient items",
                    persona_name,
                    len(data["recipes"]),
                    len(data["meals"]),
                    len(data["ingredients"]),
                )

            return results

    finally:
        await engine.dispose()


# Helper functions


def _extract_first_name(persona_name: str) -> str:
    """Extract first name from persona name (e.g., 'veggie_val' -> 'Val')."""
    parts = persona_name.split("_")
    if len(parts) >= 2:
        return parts[-1].capitalize()
    return persona_name.capitalize()


def _parse_recipe_times(tags: list[str]) -> tuple[int | None, int | None]:
    """Parse prep and cook times from recipe tags.

    Args:
        tags: List of recipe tags (may contain "30min", "60min", etc.)

    Returns:
        Tuple of (prep_time, cook_time) in minutes
    """
    for tag in tags:
        if tag.endswith("min"):
            try:
                total = int(tag[:-3])
                # Assume 1/3 prep, 2/3 cook
                return total // 3, (total * 2) // 3
            except ValueError:
                continue
    return 15, 30  # Default


def _infer_difficulty(tags: list[str]) -> str:
    """Infer recipe difficulty from tags.

    Returns valid RecipeDifficulty enum values: 'easy', 'medium', or 'hard'.
    """
    tag_set = {t.lower() for t in tags}
    if "complex" in tag_set or "advanced" in tag_set or "hard" in tag_set:
        return "hard"
    if "intermediate" in tag_set or "medium" in tag_set:
        return "medium"
    if "easy" in tag_set or "quick" in tag_set:
        return "easy"
    return "medium"


def _infer_ethnicity(tags: list[str]) -> str | None:
    """Infer cuisine/ethnicity from tags."""
    cuisines = [
        "italian",
        "mexican",
        "asian",
        "indian",
        "thai",
        "japanese",
        "korean",
        "vietnamese",
        "mediterranean",
        "greek",
        "french",
        "american",
        "middle-eastern",
    ]
    tag_set = {t.lower() for t in tags}
    for cuisine in cuisines:
        if cuisine in tag_set:
            return cuisine.title()
    return None


def _generate_recipe_description(recipe_data: RecipeData) -> str:
    """Generate a placeholder description for a recipe."""
    name = recipe_data["name"]
    tags = recipe_data.get("tags", [])
    tag_str = ", ".join(tags[:3]) if tags else "homemade"
    return f"A delicious {tag_str} {name.lower()} recipe."


def _generate_placeholder_instructions(recipe_name: str) -> list[str]:
    """Generate placeholder cooking instructions."""
    return [
        f"Gather all ingredients for {recipe_name}.",
        "Prepare and measure all ingredients.",
        "Follow the cooking method appropriate for this dish.",
        "Season to taste.",
        "Serve and enjoy!",
    ]


if __name__ == "__main__":
    asyncio.run(run_seeding())
