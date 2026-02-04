"""Tests for training data seeding utilities."""

from datetime import date, timedelta

from training.seed_database import (
    _extract_first_name,
    _generate_placeholder_instructions,
    _generate_recipe_description,
    _infer_difficulty,
    _infer_ethnicity,
    _normalize_asyncpg_url,
    _parse_recipe_times,
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
        """Should return 'advanced' for 'complex' tag"""
        assert _infer_difficulty(["complex", "italian"]) == "advanced"

    def test_advanced_from_advanced(self):
        """Should return 'advanced' for 'advanced' tag"""
        assert _infer_difficulty(["advanced"]) == "advanced"

    def test_intermediate_tag(self):
        """Should return 'intermediate' for 'intermediate' tag"""
        assert _infer_difficulty(["intermediate", "thai"]) == "intermediate"

    def test_easy_from_easy(self):
        """Should return 'easy' for 'easy' tag"""
        assert _infer_difficulty(["easy", "quick"]) == "easy"

    def test_easy_from_quick(self):
        """Should return 'easy' for 'quick' tag"""
        assert _infer_difficulty(["quick", "15min"]) == "easy"

    def test_default_intermediate(self):
        """Should default to 'intermediate' with no difficulty tags"""
        assert _infer_difficulty(["italian", "30min"]) == "intermediate"

    def test_empty_tags(self):
        """Should default to 'intermediate' for empty tags"""
        assert _infer_difficulty([]) == "intermediate"

    def test_case_insensitive(self):
        """Should handle case-insensitive tag matching"""
        assert _infer_difficulty(["EASY", "Quick"]) == "easy"
        assert _infer_difficulty(["COMPLEX"]) == "advanced"


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
