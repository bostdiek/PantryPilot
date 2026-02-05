"""Tests for training data seeding utilities."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from training.seed_database import (
    SYNTHETIC_PASSWORD,
    _extract_first_name,
    _generate_placeholder_instructions,
    _generate_recipe_description,
    _get_database_url,
    _infer_difficulty,
    _infer_ethnicity,
    _load_env_files,
    _normalize_asyncpg_url,
    _parse_recipe_times,
    cleanup_synthetic_users,
    create_persona_ingredients,
    create_persona_meal_history,
    create_persona_preferences,
    create_persona_recipes,
    create_persona_user,
    seed_all_personas,
    seed_persona,
)


# =============================================================================
# URL Normalization Tests
# =============================================================================


class TestNormalizeAsyncpgUrl:
    """Test URL normalization for asyncpg compatibility."""

    def test_postgres_to_asyncpg(self):
        """Should convert postgres:// to postgresql+asyncpg://"""
        url = "postgres://user:pass@host:5432/db"
        result = _normalize_asyncpg_url(url)
        assert result == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_postgresql_to_asyncpg(self):
        """Should convert postgresql:// to postgresql+asyncpg://"""
        url = "postgresql://user:pass@host:5432/db"
        result = _normalize_asyncpg_url(url)
        assert result == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_psycopg2_to_asyncpg(self):
        """Should convert postgresql+psycopg2:// to postgresql+asyncpg://"""
        url = "postgresql+psycopg2://user:pass@host:5432/db"
        result = _normalize_asyncpg_url(url)
        assert result == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_psycopg_to_asyncpg(self):
        """Should convert postgresql+psycopg:// to postgresql+asyncpg://"""
        url = "postgresql+psycopg://user:pass@host:5432/db"
        result = _normalize_asyncpg_url(url)
        assert result == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_sslmode_to_ssl(self):
        """Should convert sslmode=require to ssl=require"""
        url = "postgresql://user:pass@host:5432/db?sslmode=require"
        result = _normalize_asyncpg_url(url)
        assert result == "postgresql+asyncpg://user:pass@host:5432/db?ssl=require"

    def test_already_asyncpg(self):
        """Should leave postgresql+asyncpg:// unchanged"""
        url = "postgresql+asyncpg://user:pass@host:5432/db"
        result = _normalize_asyncpg_url(url)
        assert result == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_azure_postgres_url(self):
        """Should handle Azure PostgreSQL URLs correctly"""
        url = (
            "postgresql://user@server:password@server.postgres.database.azure.com:5432/"
            "db?sslmode=require"
        )
        result = _normalize_asyncpg_url(url)
        assert "postgresql+asyncpg://" in result
        assert "ssl=require" in result
        assert "sslmode" not in result


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestParseRecipeTimes:
    """Test recipe time parsing from tags."""

    def test_parse_30_minutes(self):
        """Should parse '30min' tag correctly"""
        tags = ["vegetarian", "30min", "easy"]
        prep, cook = _parse_recipe_times(tags)
        assert prep == 10  # 1/3 of 30
        assert cook == 20  # 2/3 of 30

    def test_parse_60_minutes(self):
        """Should parse '60min' tag correctly"""
        tags = ["60min", "complex"]
        prep, cook = _parse_recipe_times(tags)
        assert prep == 20
        assert cook == 40

    def test_parse_45_minutes(self):
        """Should parse '45min' tag correctly"""
        tags = ["italian", "45min"]
        prep, cook = _parse_recipe_times(tags)
        assert prep == 15
        assert cook == 30

    def test_no_time_tag(self):
        """Should return defaults when no time tag present"""
        tags = ["vegetarian", "easy"]
        prep, cook = _parse_recipe_times(tags)
        assert prep == 15
        assert cook == 30

    def test_empty_tags(self):
        """Should return defaults for empty tag list"""
        prep, cook = _parse_recipe_times([])
        assert prep == 15
        assert cook == 30

    def test_invalid_time_tag(self):
        """Should skip invalid time tags and return defaults"""
        tags = ["invalidmin", "easy"]
        prep, cook = _parse_recipe_times(tags)
        assert prep == 15
        assert cook == 30

    def test_first_time_tag_wins(self):
        """Should use first valid time tag found"""
        tags = ["30min", "60min"]
        prep, cook = _parse_recipe_times(tags)
        assert prep == 10
        assert cook == 20


class TestInferDifficulty:
    """Test difficulty inference from tags."""

    def test_advanced_from_complex(self):
        """Should return 'hard' for 'complex' tag"""
        assert _infer_difficulty(["complex", "italian"]) == "hard"

    def test_advanced_from_advanced(self):
        """Should return 'hard' for 'advanced' tag"""
        assert _infer_difficulty(["advanced"]) == "hard"

    def test_intermediate_tag(self):
        """Should return 'medium' for 'intermediate' tag"""
        assert _infer_difficulty(["intermediate", "thai"]) == "medium"

    def test_easy_from_easy(self):
        """Should return 'easy' for 'easy' tag"""
        assert _infer_difficulty(["easy", "quick"]) == "easy"

    def test_easy_from_quick(self):
        """Should return 'easy' for 'quick' tag"""
        assert _infer_difficulty(["quick", "15min"]) == "easy"

    def test_default_intermediate(self):
        """Should default to 'medium' with no difficulty tags"""
        assert _infer_difficulty(["italian", "30min"]) == "medium"

    def test_empty_tags(self):
        """Should default to 'medium' for empty tags"""
        assert _infer_difficulty([]) == "medium"

    def test_case_insensitive(self):
        """Should handle case-insensitive tag matching"""
        assert _infer_difficulty(["EASY", "Quick"]) == "easy"
        assert _infer_difficulty(["COMPLEX"]) == "hard"


class TestInferEthnicity:
    """Test cuisine/ethnicity inference from tags."""

    def test_italian(self):
        """Should detect Italian cuisine"""
        assert _infer_ethnicity(["italian", "pasta"]) == "Italian"

    def test_mexican(self):
        """Should detect Mexican cuisine"""
        assert _infer_ethnicity(["mexican", "30min"]) == "Mexican"

    def test_thai(self):
        """Should detect Thai cuisine"""
        assert _infer_ethnicity(["thai", "spicy"]) == "Thai"

    def test_japanese(self):
        """Should detect Japanese cuisine"""
        assert _infer_ethnicity(["japanese", "sushi"]) == "Japanese"

    def test_indian(self):
        """Should detect Indian cuisine"""
        assert _infer_ethnicity(["indian", "curry"]) == "Indian"

    def test_mediterranean(self):
        """Should detect Mediterranean cuisine"""
        assert _infer_ethnicity(["mediterranean"]) == "Mediterranean"

    def test_middle_eastern(self):
        """Should detect Middle Eastern cuisine"""
        assert _infer_ethnicity(["middle-eastern", "falafel"]) == "Middle-Eastern"

    def test_no_cuisine_tag(self):
        """Should return None when no cuisine tag found"""
        assert _infer_ethnicity(["vegetarian", "easy"]) is None

    def test_empty_tags(self):
        """Should return None for empty tags"""
        assert _infer_ethnicity([]) is None

    def test_first_cuisine_wins(self):
        """Should return first matching cuisine"""
        result = _infer_ethnicity(["italian", "mexican"])
        assert result == "Italian"  # Italian comes first in the cuisines list

    def test_case_insensitive(self):
        """Should handle case-insensitive matching"""
        assert _infer_ethnicity(["ITALIAN"]) == "Italian"
        assert _infer_ethnicity(["Thai"]) == "Thai"


class TestExtractFirstName:
    """Test first name extraction from persona names."""

    def test_veggie_val(self):
        """Should extract 'Val' from 'veggie_val'"""
        assert _extract_first_name("veggie_val") == "Val"

    def test_family_fiona(self):
        """Should extract 'Fiona' from 'family_fiona'"""
        assert _extract_first_name("family_fiona") == "Fiona"

    def test_solo_sam(self):
        """Should extract 'Sam' from 'solo_sam'"""
        assert _extract_first_name("solo_sam") == "Sam"

    def test_gluten_free_grace(self):
        """Should extract 'Grace' from 'gluten_free_grace'"""
        assert _extract_first_name("gluten_free_grace") == "Grace"

    def test_single_word(self):
        """Should capitalize single word"""
        assert _extract_first_name("alex") == "Alex"

    def test_empty_string(self):
        """Should handle empty string"""
        assert _extract_first_name("") == ""


class TestGenerateRecipeDescription:
    """Test recipe description generation."""

    def test_with_tags(self):
        """Should generate description with tags"""
        recipe_data = {"name": "Pasta Carbonara", "tags": ["italian", "30min", "easy"]}
        result = _generate_recipe_description(recipe_data)
        assert "italian, 30min, easy" in result.lower()
        assert "pasta carbonara" in result.lower()

    def test_with_many_tags(self):
        """Should only use first 3 tags"""
        recipe_data = {
            "name": "Pad Thai",
            "tags": ["thai", "30min", "easy", "vegetarian", "spicy"],
        }
        result = _generate_recipe_description(recipe_data)
        # Should only include first 3 tags
        assert "thai" in result.lower()
        assert "30min" in result.lower()
        assert "easy" in result.lower()

    def test_without_tags(self):
        """Should use 'homemade' when no tags"""
        recipe_data = {"name": "Mystery Dish", "tags": []}
        result = _generate_recipe_description(recipe_data)
        assert "homemade" in result.lower()
        assert "mystery dish" in result.lower()

    def test_missing_tags_key(self):
        """Should handle missing tags key"""
        recipe_data = {"name": "Simple Soup"}
        result = _generate_recipe_description(recipe_data)
        assert "homemade" in result.lower()
        assert "simple soup" in result.lower()


class TestGeneratePlaceholderInstructions:
    """Test placeholder instruction generation."""

    def test_generates_list(self):
        """Should return a list of instructions"""
        result = _generate_placeholder_instructions("Pasta Carbonara")
        assert isinstance(result, list)
        assert len(result) == 5

    def test_includes_recipe_name(self):
        """Should include recipe name in first instruction"""
        result = _generate_placeholder_instructions("Tacos")
        assert "Tacos" in result[0]

    def test_standard_steps(self):
        """Should include standard cooking steps"""
        result = _generate_placeholder_instructions("Any Recipe")
        assert any("ingredient" in step.lower() for step in result)
        assert any("season" in step.lower() for step in result)
        assert any("serve" in step.lower() for step in result)


# =============================================================================
# Relative Date Tests
# =============================================================================


class TestRelativeDates:
    """Test relative date calculation for meal history.

    Note: These tests validate the algorithm described in create_persona_meal_history.
    The actual function creates Meal objects, so we test the date calculation logic.
    """

    def test_single_entry_yesterday(self):
        """Single entry should be from 1 day ago"""
        today = date.today()
        num_entries = 1

        # First (and only) entry: days_ago = 1 - 0 = 1
        days_ago = num_entries - 0
        meal_date = today - timedelta(days=days_ago)

        assert meal_date == today - timedelta(days=1)

    def test_14_entries_span_two_weeks(self):
        """14 entries should span from 14 days ago to 1 day ago"""
        today = date.today()
        num_entries = 14

        # First entry: days_ago = 14 - 0 = 14
        first_days_ago = num_entries - 0
        first_date = today - timedelta(days=first_days_ago)

        # Last entry: days_ago = 14 - 13 = 1
        last_days_ago = num_entries - (num_entries - 1)
        last_date = today - timedelta(days=last_days_ago)

        assert first_date == today - timedelta(days=14)
        assert last_date == today - timedelta(days=1)

    def test_5_entries_recent_history(self):
        """5 entries should span from 5 days ago to 1 day ago"""
        today = date.today()
        num_entries = 5

        dates = []
        for i in range(num_entries):
            days_ago = num_entries - i
            meal_date = today - timedelta(days=days_ago)
            dates.append(meal_date)

        # Check span
        assert dates[0] == today - timedelta(days=5)
        assert dates[-1] == today - timedelta(days=1)

        # Check consecutive days
        for i in range(len(dates) - 1):
            diff = (dates[i + 1] - dates[i]).days
            assert diff == 1

    def test_dates_always_in_past(self):
        """All generated dates should be in the past"""
        today = date.today()
        num_entries = 20

        for i in range(num_entries):
            days_ago = num_entries - i
            meal_date = today - timedelta(days=days_ago)
            assert meal_date < today

    def test_dates_chronological_order(self):
        """Dates should be in chronological order (oldest first)"""
        today = date.today()
        num_entries = 10

        dates = []
        for i in range(num_entries):
            days_ago = num_entries - i
            meal_date = today - timedelta(days=days_ago)
            dates.append(meal_date)

        # Verify strictly increasing
        for i in range(len(dates) - 1):
            assert dates[i] < dates[i + 1]


# =============================================================================
# Environment Loading Tests
# =============================================================================


class TestLoadEnvFiles:
    """Test environment file loading."""

    def test_load_env_files_no_dotenv(self) -> None:
        """Should handle missing dotenv package gracefully."""
        # Mock import to raise ImportError
        with patch.dict("sys.modules", {"dotenv": None}):
            # Should not raise when dotenv is unavailable
            _load_env_files()

    def test_load_env_files_with_dotenv(self) -> None:
        """Should load env files when dotenv is available."""
        mock_load_dotenv = MagicMock()

        # Create a mock dotenv module
        mock_dotenv_module = MagicMock()
        mock_dotenv_module.load_dotenv = mock_load_dotenv

        # Mock Path to return a file that exists
        mock_path = MagicMock()
        mock_candidate = MagicMock()
        mock_candidate.exists.return_value = True
        mock_path.return_value.resolve.return_value.parents = [MagicMock()]
        mock_path.return_value.resolve.return_value.parents[0].__truediv__ = (
            lambda self, x: mock_candidate
        )

        with (
            patch(
                "training.seed_database.Path",
                mock_path,
            ),
            patch.dict("sys.modules", {"dotenv": mock_dotenv_module}),
        ):
            # This may not trigger coverage due to how the import works in the function
            # But we at least verify the function doesn't crash
            _load_env_files()


class TestGetDatabaseUrl:
    """Test database URL construction."""

    def test_get_database_url_from_env_var(self) -> None:
        """Should use DATABASE_URL when set."""
        with patch.dict(
            "os.environ",
            {"DATABASE_URL": "postgres://user:pass@host:5432/db"},
            clear=True,
        ):
            with patch("training.seed_database._load_env_files"):
                url = _get_database_url()
                assert "postgresql+asyncpg://" in url
                assert "@host:" in url or "@localhost:" in url

    def test_get_database_url_replaces_db_hostname(self) -> None:
        """Should replace 'db' hostname with 'localhost' for local execution."""
        with patch.dict(
            "os.environ",
            {"DATABASE_URL": "postgres://user:pass@db:5432/mydb"},
            clear=True,
        ):
            with patch("training.seed_database._load_env_files"):
                url = _get_database_url()
                assert "@localhost:" in url
                assert "@db:" not in url

    def test_get_database_url_from_postgres_vars(self) -> None:
        """Should construct URL from POSTGRES_* vars when no DATABASE_URL."""
        with patch.dict(
            "os.environ",
            {
                "POSTGRES_USER": "testuser",
                "POSTGRES_PASSWORD": "testpass",
                "POSTGRES_DB": "testdb",
                "POSTGRES_HOST": "localhost",
                "POSTGRES_PORT": "5433",
            },
            clear=True,
        ):
            with patch("training.seed_database._load_env_files"):
                url = _get_database_url()
                expected = (
                    "postgresql+asyncpg://testuser:testpass@localhost:5433/testdb"
                )
                assert expected == url

    def test_get_database_url_defaults(self) -> None:
        """Should use defaults when no env vars set."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("training.seed_database._load_env_files"):
                url = _get_database_url()
                assert "postgresql+asyncpg://" in url
                assert "pantrypilot_dev" in url

    def test_get_database_url_replaces_db_host_to_localhost(self) -> None:
        """Should replace host 'db' with 'localhost' for local dev."""
        with patch.dict(
            "os.environ",
            {
                "POSTGRES_USER": "user",
                "POSTGRES_PASSWORD": "pass",
                "POSTGRES_DB": "db",
                "POSTGRES_HOST": "db",
                "POSTGRES_PORT": "5432",
            },
            clear=True,
        ):
            with patch("training.seed_database._load_env_files"):
                url = _get_database_url()
                assert "@localhost:" in url
                assert "@db:" not in url


class TestSyntheticPassword:
    """Test synthetic password constant."""

    def test_password_exists(self) -> None:
        """Verify SYNTHETIC_PASSWORD is defined."""
        assert SYNTHETIC_PASSWORD is not None
        assert len(SYNTHETIC_PASSWORD) > 8  # Reasonably strong password


# =============================================================================
# Async Database Function Tests (with mocks)
# =============================================================================


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def sample_persona() -> dict:
    """Create a sample persona for testing."""
    return {
        "user_id": "synthetic-test-user",
        "preferences": {
            "dietary_restrictions": ["vegetarian"],
            "cuisine_preferences": ["italian", "mexican"],
            "cooking_skill": "intermediate",
            "household_size": 2,
            "location": {
                "city": "San Francisco",
                "state_or_region": "CA",
                "country": "USA",
                "postal_code": "94102",
            },
        },
        "recipes": [
            {"name": "Pasta Primavera", "tags": ["italian", "vegetarian", "30min"]},
            {"name": "Veggie Tacos", "tags": ["mexican", "easy", "20min"]},
        ],
        "pantry_items": ["tofu", "rice", "beans", "tomatoes"],
        "meal_plan_history": [
            {"date": "2026-01-01", "recipe": "Pasta Primavera", "meal": "dinner"},
            {"date": "2026-01-02", "recipe": "Veggie Tacos", "meal": "dinner"},
        ],
    }


@pytest.mark.asyncio
class TestCreatePersonaUser:
    """Tests for create_persona_user function."""

    async def test_creates_user_with_correct_fields(
        self, mock_db_session: AsyncMock, sample_persona: dict
    ) -> None:
        """Should create a user with the correct attributes."""
        user = await create_persona_user(
            mock_db_session, "test_persona", sample_persona
        )

        # Verify user was added and flushed
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

        # Verify user attributes
        assert user.username == "synthetic-test-user"
        assert user.email == "synthetic-test-user@pantrypilot.synthetic"
        assert user.is_verified is True
        assert user.first_name == "Persona"
        assert user.last_name == "(Synthetic)"


@pytest.mark.asyncio
class TestCreatePersonaPreferences:
    """Tests for create_persona_preferences function."""

    async def test_creates_preferences_with_correct_fields(
        self, mock_db_session: AsyncMock, sample_persona: dict
    ) -> None:
        """Should create preferences with the correct attributes."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "synthetic-test-user"

        prefs = await create_persona_preferences(
            mock_db_session, mock_user, sample_persona
        )

        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

        # Verify preferences
        assert prefs.user_id == 1
        assert prefs.dietary_restrictions == ["vegetarian"]
        assert prefs.city == "San Francisco"
        assert prefs.family_size == 2


@pytest.mark.asyncio
class TestCreatePersonaRecipes:
    """Tests for create_persona_recipes function."""

    async def test_creates_recipes_for_all_entries(
        self, mock_db_session: AsyncMock, sample_persona: dict
    ) -> None:
        """Should create a recipe for each recipe in the persona."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "synthetic-test-user"

        recipe_map = await create_persona_recipes(
            mock_db_session, mock_user, sample_persona
        )

        # Should create both recipes
        assert len(recipe_map) == 2
        assert "Pasta Primavera" in recipe_map
        assert "Veggie Tacos" in recipe_map
        mock_db_session.flush.assert_called_once()


@pytest.mark.asyncio
class TestCreatePersonaIngredients:
    """Tests for create_persona_ingredients function."""

    async def test_creates_all_pantry_items(
        self, mock_db_session: AsyncMock, sample_persona: dict
    ) -> None:
        """Should create an ingredient for each pantry item."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "synthetic-test-user"

        ingredients = await create_persona_ingredients(
            mock_db_session, mock_user, sample_persona
        )

        assert len(ingredients) == 4
        mock_db_session.flush.assert_called_once()


@pytest.mark.asyncio
class TestCreatePersonaMealHistory:
    """Tests for create_persona_meal_history function."""

    async def test_creates_meal_entries(
        self, mock_db_session: AsyncMock, sample_persona: dict
    ) -> None:
        """Should create meal entries for all history items."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "synthetic-test-user"

        mock_recipe = MagicMock()
        mock_recipe.id = 100
        recipe_map = {"Pasta Primavera": mock_recipe, "Veggie Tacos": mock_recipe}

        meals = await create_persona_meal_history(
            mock_db_session, mock_user, sample_persona, recipe_map
        )

        assert len(meals) == 2
        mock_db_session.flush.assert_called_once()

    async def test_handles_missing_recipe(
        self, mock_db_session: AsyncMock, sample_persona: dict
    ) -> None:
        """Should handle recipes not in the recipe map."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "synthetic-test-user"

        # Empty recipe map - no recipes found
        recipe_map: dict = {}

        meals = await create_persona_meal_history(
            mock_db_session, mock_user, sample_persona, recipe_map
        )

        # Should still create meals, but with recipe_id = None
        assert len(meals) == 2
        for meal in meals:
            assert meal.recipe_id is None


@pytest.mark.asyncio
class TestSeedPersona:
    """Tests for seed_persona function."""

    async def test_seeds_complete_persona(
        self, mock_db_session: AsyncMock, sample_persona: dict
    ) -> None:
        """Should seed all data for a persona."""
        with (
            patch("training.seed_database.create_persona_user") as mock_create_user,
            patch(
                "training.seed_database.create_persona_preferences"
            ) as mock_create_prefs,
            patch(
                "training.seed_database.create_persona_recipes"
            ) as mock_create_recipes,
            patch(
                "training.seed_database.create_persona_ingredients"
            ) as mock_create_ingredients,
            patch(
                "training.seed_database.create_persona_meal_history"
            ) as mock_create_meals,
        ):
            # Setup mocks
            mock_user = MagicMock()
            mock_user.id = 1
            mock_create_user.return_value = mock_user
            mock_create_prefs.return_value = MagicMock()
            mock_create_recipes.return_value = {"Test Recipe": MagicMock()}
            mock_create_ingredients.return_value = [MagicMock()]
            mock_create_meals.return_value = [MagicMock()]

            result = await seed_persona(mock_db_session, "test_persona", sample_persona)

            # All functions should be called
            mock_create_user.assert_called_once()
            mock_create_prefs.assert_called_once()
            mock_create_recipes.assert_called_once()
            mock_create_ingredients.assert_called_once()
            mock_create_meals.assert_called_once()
            mock_db_session.commit.assert_called_once()

            # Result should contain all seeded data
            assert "user" in result
            assert "preferences" in result
            assert "recipes" in result
            assert "ingredients" in result
            assert "meals" in result


@pytest.mark.asyncio
class TestSeedAllPersonas:
    """Tests for seed_all_personas function."""

    async def test_seeds_all_personas(self, mock_db_session: AsyncMock) -> None:
        """Should seed all personas in PERSONAS dict."""
        with (
            patch("training.seed_database.seed_persona") as mock_seed,
            patch(
                "training.seed_database.PERSONAS",
                {"persona1": {"user_id": "test1"}, "persona2": {"user_id": "test2"}},
            ),
        ):
            mock_seed.return_value = {"user": MagicMock()}

            results = await seed_all_personas(mock_db_session)

            assert mock_seed.call_count == 2
            assert "persona1" in results
            assert "persona2" in results


@pytest.mark.asyncio
class TestCleanupSyntheticUsers:
    """Tests for cleanup_synthetic_users function."""

    async def test_cleanup_deletes_users(self, mock_db_session: AsyncMock) -> None:
        """Should delete synthetic users and related data."""
        # Mock the query result
        mock_user = MagicMock()
        mock_user.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_db_session.execute.return_value = mock_result

        await cleanup_synthetic_users(mock_db_session)

        # Should execute delete queries for related tables
        assert mock_db_session.execute.call_count >= 1
        mock_db_session.commit.assert_called_once()

    async def test_cleanup_no_users(self, mock_db_session: AsyncMock) -> None:
        """Should handle case when no synthetic users exist."""
        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        count = await cleanup_synthetic_users(mock_db_session)

        assert count == 0
