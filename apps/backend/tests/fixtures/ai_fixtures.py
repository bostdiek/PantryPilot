"""Test fixtures and factories for AI extraction functionality.

This module provides reusable test data and factory functions to replace
complex manual mock construction with fixture-based approach, dramatically
simplifying test files and improving maintainability.
"""

import random
from datetime import UTC, datetime, timedelta
from typing import Any, get_origin
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import BaseModel  # type: ignore[import-not-found]

from schemas.ai import (
    AIGeneratedRecipe,
    AIRecipeFromUrlRequest,
    ExtractionFailureResponse,
    ExtractionNotFound,
    RecipeExtractionResult,
)
from schemas.recipes import IngredientIn, RecipeCategory, RecipeCreate, RecipeDifficulty


class TestModel:
    """Custom test data generator for Pydantic models with realistic data generation."""

    def __init__(self, model_class: type[BaseModel]):
        self.model_class = model_class

    def generate(self, **overrides) -> BaseModel:
        """Generate a model instance with realistic test data.

        Caller may override any field by supplying keyword arguments.
        """
        # Get model fields
        fields = self.model_class.model_fields

        # Generate field values based on type and constraints
        field_values = {}

        for field_name, field_info in fields.items():
            if field_name in overrides:
                field_values[field_name] = overrides[field_name]
            else:
                field_values[field_name] = self._generate_field_value(field_info)

        return self.model_class(**field_values)

    def _generate_field_value(self, field_info) -> Any:
        """Generate a realistic value for a field based on its type and constraints."""
        field_type = field_info.annotation
        default_value = field_info.default

        # If field has a default, use it
        if default_value is not ...:  # ... means no default
            return default_value

        # Handle different field types
        if field_type is str:
            return self._generate_string_field(field_info)
        elif field_type is int:
            return self._generate_int_field(field_info)
        elif field_type is float:
            return self._generate_float_field(field_info)
        elif field_type is bool:
            return self._generate_bool_field(field_info)
        elif field_type is list:
            return self._generate_list_field(field_info)
        elif get_origin(field_type) in (list, list):
            return self._generate_list_field(field_info)
        elif hasattr(field_type, "__origin__") and field_type.__origin__ in (
            list,
            list,
        ):
            return self._generate_list_field(field_info)
        else:
            # For complex types, try to create with defaults
            try:
                return field_type()
            except Exception:  # pragma: no cover - defensive fallback
                return None

    def _generate_string_field(self, field_info) -> str:
        """Generate realistic string values."""
        # Check for enum constraints
        if hasattr(field_info.annotation, "__args__"):
            # This might be an Enum or constrained string
            pass

        # Generate based on field name patterns
        field_name = (
            field_info.annotation.__name__
            if hasattr(field_info.annotation, "__name__")
            else str(field_info.annotation)
        )

        if "title" in field_name.lower():
            return "Delicious Test Recipe"
        elif "description" in field_name.lower():
            return (
                "A wonderful test recipe with realistic ingredients "
                "and clear instructions"
            )
        elif "notes" in field_name.lower():
            return "Test notes for recipe validation"
        elif "url" in field_name.lower():
            return "https://example.com/test-recipe"
        elif "ethnicity" in field_name.lower():
            return "american"
        else:
            return f"test_{field_name.lower()}"

    def _generate_int_field(self, field_info) -> int:
        """Generate realistic integer values."""
        if hasattr(field_info, "ge") and field_info.ge is not None:
            min_val = field_info.ge
        else:
            min_val = 1

        if hasattr(field_info, "le") and field_info.le is not None:
            max_val = field_info.le
        else:
            max_val = min_val * 10

        return random.randint(min_val, max_val)

    def _generate_float_field(self, field_info) -> float:
        """Generate realistic float values."""
        if hasattr(field_info, "ge") and field_info.ge is not None:
            min_val = field_info.ge
        else:
            min_val = 0.0

        if hasattr(field_info, "le") and field_info.le is not None:
            max_val = field_info.le
        else:
            max_val = 10.0

        return round(random.uniform(min_val, max_val), 2)

    def _generate_bool_field(self, field_info) -> bool:
        """Generate boolean values."""
        return random.choice([True, False])

    def _generate_list_field(self, field_info) -> list:
        """Generate realistic list values."""
        # For now, return empty list - can be enhanced for specific types
        return []


# ============================================================================
# STANDARD TEST DATA FIXTURES
# ============================================================================


@pytest.fixture
def sample_recipe_data():
    """Standard recipe data fixture (realistic but concise)."""
    # Use TestModel to generate realistic recipe data with proper validation
    test_model = TestModel(RecipeCreate)

    # Generate a realistic recipe with proper relationships and constraints
    return test_model.generate(
        title="Chicken Parmesan",
        description=(
            "A classic Italian-American dish with breaded chicken, marinara sauce, "
            "and melted cheese"
        ),
        prep_time_minutes=20,
        cook_time_minutes=35,
        serving_min=4,
        serving_max=6,
        instructions=[
            "Preheat oven to 400°F and prepare breading station",
            "Bread chicken cutlets with flour, egg, and breadcrumbs",
            "Heat oil in skillet and brown chicken on both sides",
            "Transfer to baking dish and top with marinara and cheese",
            "Bake until cheese is melted and bubbly",
        ],
        difficulty=RecipeDifficulty.MEDIUM,
        category=RecipeCategory.DINNER,
        ingredients=[
            IngredientIn(
                name="boneless chicken breasts",
                quantity_value=4.0,
                quantity_unit="pieces",
                prep={"method": "pounded", "size_descriptor": "thin"},
                is_optional=False,
            ),
            IngredientIn(
                name="marinara sauce",
                quantity_value=2.0,
                quantity_unit="cups",
                is_optional=False,
            ),
            IngredientIn(
                name="mozzarella cheese",
                quantity_value=1.5,
                quantity_unit="cups",
                prep={"method": "shredded"},
                is_optional=False,
            ),
            IngredientIn(
                name="parmesan cheese",
                quantity_value=0.5,
                quantity_unit="cup",
                prep={"method": "grated"},
                is_optional=False,
            ),
            IngredientIn(
                name="fresh basil leaves",
                quantity_value=0.25,
                quantity_unit="cup",
                prep={"method": "chopped"},
                is_optional=True,
            ),
        ],
        ethnicity="italian-american",
        oven_temperature_f=400,
        user_notes="For best results, use homemade marinara sauce",
    )


@pytest.fixture
def sample_extraction_result(sample_recipe_data):
    """Standard `RecipeExtractionResult` fixture (realistic data)."""
    # Use TestModel to generate realistic extraction result with proper AI metadata
    test_model = TestModel(RecipeExtractionResult)

    # Merge model dump with overrides but avoid duplicate keys by removing
    # any keys from the dumped dict that will be provided explicitly.
    base = sample_recipe_data.model_dump()
    overrides = {
        "confidence_score": 0.87,
        "extraction_notes": (
            "Successfully extracted recipe with high confidence. All required "
            "fields present and well-structured."
        ),
        "link_source": "https://example.com/chicken-parmesan-recipe",
    }
    for k in overrides:
        base.pop(k, None)

    return test_model.generate(
        **base,
        **overrides,
    )


@pytest.fixture
def sample_ai_generated_recipe(sample_recipe_data):
    """Standard `AIGeneratedRecipe` fixture (realistic data)."""
    # Use TestModel to generate realistic AI-generated recipe with proper metadata
    test_model = TestModel(AIGeneratedRecipe)

    return test_model.generate(
        recipe_data=sample_recipe_data,
        confidence_score=0.87,
        source_url="https://example.com/chicken-parmesan-recipe",
        extraction_notes=(
            "High-quality extraction with well-structured ingredients and clear "
            "instructions. Recipe appears complete and cookable."
        ),
    )


@pytest.fixture
def extraction_not_found():
    """Standard ExtractionNotFound response."""
    return ExtractionNotFound(reason="No recipe found on this page")


@pytest.fixture
def extraction_failure_response():
    """Standard ExtractionFailureResponse."""
    return ExtractionFailureResponse(
        reason="Extraction failed",
        source_url="https://example.com/recipe",
        details={"error_type": "network_timeout"},
    )


# ============================================================================
# MOCK HTML CONTENT FIXTURES
# ============================================================================


@pytest.fixture
def mock_recipe_html():
    """Standard mock HTML with recipe content."""
    return """
    <html>
        <head><title>Delicious Recipe</title></head>
        <body>
            <h1>Chicken Parmesan</h1>
            <p>A classic Italian-American dish</p>
            <div class="ingredients">
                <h2>Ingredients</h2>
                <ul>
                    <li>2 chicken breasts</li>
                    <li>1 cup marinara sauce</li>
                    <li>1 cup mozzarella cheese</li>
                </ul>
            </div>
            <div class="instructions">
                <h2>Instructions</h2>
                <ol>
                    <li>Prep the chicken</li>
                    <li>Bake at 350°F for 25 minutes</li>
                    <li>Add cheese and bake 5 more minutes</li>
                </ol>
            </div>
            <script>alert('evil script')</script>
        </body>
    </html>
    """


@pytest.fixture
def mock_non_recipe_html():
    """Mock HTML without recipe content."""
    return """
    <html>
        <head><title>Search Results</title></head>
        <body>
            <h1>Search Results for "recipe"</h1>
            <p>No recipes found on this page.</p>
            <div class="search-results">
                <div>Result 1: Not a recipe</div>
                <div>Result 2: Still not a recipe</div>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def mock_empty_html():
    """Mock empty HTML content."""
    return ""


@pytest.fixture
def mock_malformed_html():
    """Mock malformed HTML content."""
    return "<html><body><h1>Unclosed tag"


# ============================================================================
# MOCK USER AND DRAFT FIXTURES
# ============================================================================


@pytest.fixture
def mock_user_data():
    """Standard mock user data."""
    return {
        "id": uuid4(),
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": "hashed_password",  # pragma: allowlist secret
    }


@pytest.fixture
def mock_user(mock_user_data):
    """Mock User model instance."""
    from models.users import User

    user = Mock(spec=User)
    user.id = mock_user_data["id"]
    user.username = mock_user_data["username"]
    user.email = mock_user_data["email"]
    user.hashed_password = mock_user_data["hashed_password"]
    return user


@pytest.fixture
def mock_draft_data():
    """Standard mock draft data."""
    return {
        "id": uuid4(),
        "user_id": uuid4(),
        "type": "recipe_suggestion",
        "payload": {
            "generated_recipe": {
                "recipe_data": {
                    "title": "Test Recipe",
                    "instructions": ["Step 1"],
                    "ingredients": [],
                    "prep_time_minutes": 10,
                    "cook_time_minutes": 20,
                    "serving_min": 2,
                    "difficulty": "easy",
                    "category": "dinner",
                }
            }
        },
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
    }


@pytest.fixture
def mock_draft(mock_draft_data):
    """Mock AIDraft model instance."""
    from models.ai_drafts import AIDraft

    draft = Mock(spec=AIDraft)
    draft.id = mock_draft_data["id"]
    draft.user_id = mock_draft_data["user_id"]
    draft.type = mock_draft_data["type"]
    draft.payload = mock_draft_data["payload"]
    draft.expires_at = mock_draft_data["expires_at"]
    return draft


@pytest.fixture
def mock_expired_draft(mock_draft_data):
    """Mock expired AIDraft."""
    from models.ai_drafts import AIDraft

    draft = Mock(spec=AIDraft)
    draft.id = mock_draft_data["id"]
    draft.user_id = mock_draft_data["user_id"]
    draft.type = mock_draft_data["type"]
    draft.payload = mock_draft_data["payload"]
    draft.expires_at = datetime.now(UTC) - timedelta(hours=1)  # Expired
    return draft


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


def create_recipe_extraction_result(
    title: str = "Test Recipe",
    confidence_score: float = 0.85,
    difficulty: RecipeDifficulty = RecipeDifficulty.MEDIUM,
    category: RecipeCategory = RecipeCategory.DINNER,
    ingredient_count: int = 2,
    prep_time_minutes: int = 15,
    cook_time_minutes: int = 30,
    serving_min: int = 4,
    serving_max: int = 6,
    instructions: list[str] | None = None,
    extraction_notes: str = "Test extraction",
    link_source: str = "https://example.com/recipe",
    **kwargs,
) -> RecipeExtractionResult:
    """Create a `RecipeExtractionResult` with realistic data via `TestModel`.

    Provides sensible defaults; override any field with kwargs.
    """

    # Use TestModel to generate realistic recipe data with proper validation
    test_model = TestModel(RecipeExtractionResult)

    # Generate realistic ingredients with proper relationships
    ingredients = []
    for i in range(ingredient_count):
        # Use TestModel for individual ingredients too
        ingredient_test_model = TestModel(IngredientIn)
        ingredient = ingredient_test_model.generate(
            name=f"ingredient_{i + 1}",
            quantity_value=float(i + 1),
            quantity_unit="cups" if i % 2 == 0 else "tablespoons",
            is_optional=i > 0,
        )
        ingredients.append(ingredient)

    # Use provided instructions or generate realistic ones
    if instructions is None:
        instructions = [
            "Prepare all ingredients",
            "Combine ingredients according to recipe",
            "Cook following specified method",
            "Serve hot and enjoy",
        ]

    # Generate the extraction result with realistic data
    return test_model.generate(
        title=title,
        description=f"A delicious {title.lower()} recipe with authentic flavors",
        prep_time_minutes=prep_time_minutes,
        cook_time_minutes=cook_time_minutes,
        serving_min=serving_min,
        serving_max=serving_max,
        instructions=instructions,
        difficulty=difficulty,
        category=category,
        ingredients=ingredients,
        confidence_score=confidence_score,
        extraction_notes=extraction_notes,
        link_source=link_source,
        **kwargs,
    )


def create_ai_generated_recipe(
    title: str = "Test Recipe",
    confidence_score: float = 0.85,
    source_url: str = "https://example.com/recipe",
    ingredient_count: int = 2,
    prep_time_minutes: int = 15,
    cook_time_minutes: int = 30,
    serving_min: int = 4,
    serving_max: int = 6,
    instructions: list[str] | None = None,
    difficulty: RecipeDifficulty = RecipeDifficulty.MEDIUM,
    category: RecipeCategory = RecipeCategory.DINNER,
    extraction_notes: str = "Good extraction",
    **kwargs,
) -> AIGeneratedRecipe:
    """Create an `AIGeneratedRecipe` instance with realistic nested data."""

    # Use TestModel to generate realistic recipe data first
    recipe_test_model = TestModel(RecipeCreate)

    # Generate realistic ingredients with proper relationships
    ingredients = []
    for i in range(ingredient_count):
        ingredient_test_model = TestModel(IngredientIn)
        ingredient = ingredient_test_model.generate(
            name=f"ingredient_{i + 1}",
            quantity_value=float(i + 1),
            quantity_unit="cups" if i % 2 == 0 else "tablespoons",
            is_optional=i > 0,
        )
        ingredients.append(ingredient)

    # Use provided instructions or generate realistic ones
    if instructions is None:
        instructions = [
            "Prepare all ingredients and preheat oven if needed",
            "Mix ingredients according to recipe specifications",
            "Cook using specified method and temperature",
            "Rest and serve as directed",
        ]

    # Generate the recipe data with realistic content
    recipe_data = recipe_test_model.generate(
        title=title,
        description=(
            f"A delicious {title.lower()} recipe with authentic flavors and "
            "proper technique"
        ),
        prep_time_minutes=prep_time_minutes,
        cook_time_minutes=cook_time_minutes,
        serving_min=serving_min,
        serving_max=serving_max,
        instructions=instructions,
        difficulty=difficulty,
        category=category,
        ingredients=ingredients,
        **kwargs,
    )

    # Use TestModel to generate the AI-generated recipe wrapper
    ai_test_model = TestModel(AIGeneratedRecipe)

    return ai_test_model.generate(
        recipe_data=recipe_data,
        confidence_score=confidence_score,
        source_url=source_url,
        extraction_notes=extraction_notes,
    )


def create_mock_http_response(
    text: str = "", status_code: int = 200, content_type: str = "text/html", **kwargs
) -> Mock:
    """Factory function to create mock HTTP responses."""

    response = Mock()
    response.text = text
    response.content = text.encode("utf-8")
    response.headers = {"content-type": content_type}
    response.status_code = status_code
    response.raise_for_status = Mock()

    if status_code >= 400:
        response.raise_for_status.side_effect = Exception(f"{status_code} Error")

    return response


def create_test_user(
    username: str = "testuser",
    email: str = "test@example.com",
    user_id: str | None = None,
) -> Mock:
    """Factory function to create mock User objects."""

    from models.users import User

    user = Mock(spec=User)
    user.id = uuid4() if user_id is None else user_id
    user.username = username
    user.email = email
    user.hashed_password = "hashed_password"  # pragma: allowlist secret

    return user


def create_test_draft(
    user_id: str | None = None,
    draft_type: str = "recipe_suggestion",
    expires_hours: int = 1,
    **payload_kwargs,
) -> Mock:
    """Factory function to create mock AIDraft objects."""

    from models.ai_drafts import AIDraft

    draft = Mock(spec=AIDraft)
    draft.id = uuid4()
    draft.user_id = uuid4() if user_id is None else user_id
    draft.type = draft_type
    draft.payload = payload_kwargs.get("payload", {"test": "data"})
    draft.expires_at = datetime.now(UTC) + timedelta(hours=expires_hours)

    return draft


# ============================================================================
# COMMON MOCK OBJECTS AND EXCEPTIONS
# ============================================================================


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for testing."""
    # Create the mock response first
    mock_response = Mock()
    mock_response.text = "<html><body>Test</body></html>"
    mock_response.content = b"<html><body>Test</body></html>"
    mock_response.headers = {"content-type": "text/html"}
    mock_response.raise_for_status = Mock()

    # Create the mock async context manager
    mock_async_client = Mock()
    mock_async_client.get.return_value = mock_response

    # Create the main client mock
    mock_client = Mock()
    mock_client.return_value.__aenter__ = Mock(return_value=mock_async_client)
    mock_client.return_value.__aexit__ = Mock(return_value=None)

    return mock_client


@pytest.fixture
def mock_agent_run_error():
    """Mock AgentRunError for testing AI failures."""
    try:
        from pydantic_ai import AgentRunError  # type: ignore[import-not-found]

        return AgentRunError("AI agent failed")
    except ImportError:
        # Fallback for test environments without pydantic_ai
        return Exception("AI agent failed")


@pytest.fixture
def mock_validation_error():
    """Mock ValidationError for testing schema validation failures."""
    from pydantic import ValidationError  # type: ignore[import-not-found]

    try:
        raise ValidationError.from_exception_data(title="Test", line_errors=[])
    except Exception:
        return ValidationError.from_exception_data(
            title="ValidationError", line_errors=[]
        )


# ============================================================================
# SPECIALIZED TEST DATA FIXTURES
# ============================================================================


@pytest.fixture
def low_confidence_extraction():
    """RecipeExtractionResult with low confidence score using TestModel."""
    # Use TestModel to generate a realistic low-confidence extraction
    test_model = TestModel(RecipeExtractionResult)

    return test_model.generate(
        title="Ambiguous Recipe",
        description=(
            "Recipe extraction with uncertain ingredient parsing and unclear "
            "instructions"
        ),
        prep_time_minutes=25,
        cook_time_minutes=40,
        serving_min=2,
        serving_max=4,
        instructions=["Mix ingredients", "Cook until done"],
        difficulty=RecipeDifficulty.MEDIUM,
        category=RecipeCategory.DINNER,
        ingredients=[
            IngredientIn(
                name="unclear_ingredient",
                quantity_value=1.0,
                quantity_unit="cup",
                is_optional=False,
            ),
        ],
        confidence_score=0.25,
        extraction_notes=(
            "Low confidence extraction - ambiguous ingredient names and unclear "
            "cooking times detected. Manual review recommended."
        ),
        link_source="https://example.com/ambiguous-recipe",
    )


@pytest.fixture
def high_confidence_extraction():
    """RecipeExtractionResult with high confidence score using TestModel."""
    # Use TestModel to generate a realistic high-confidence extraction
    test_model = TestModel(RecipeExtractionResult)

    return test_model.generate(
        title="Classic Chocolate Chip Cookies",
        description=(
            "Perfectly crispy on the outside, chewy on the inside - the "
            "ultimate chocolate chip cookie recipe"
        ),
        prep_time_minutes=15,
        cook_time_minutes=12,
        serving_min=24,
        serving_max=36,
        instructions=[
            "Preheat oven to 375°F",
            "Cream together butter and sugars until light and fluffy",
            "Beat in eggs one at a time, then vanilla",
            "Whisk together flour, baking soda, and salt",
            "Gradually mix dry ingredients into wet ingredients",
            "Fold in chocolate chips",
            "Drop rounded tablespoons onto ungreased baking sheets",
            "Bake 9-11 minutes until golden brown",
            "Cool on baking sheet for 2 minutes before transferring to wire rack",
        ],
        difficulty=RecipeDifficulty.EASY,
        category=RecipeCategory.DESSERT,
        ingredients=[
            IngredientIn(
                name="all-purpose flour",
                quantity_value=2.25,
                quantity_unit="cups",
                is_optional=False,
            ),
            IngredientIn(
                name="butter",
                quantity_value=1.0,
                quantity_unit="cup",
                prep={"method": "softened"},
                is_optional=False,
            ),
            IngredientIn(
                name="brown sugar",
                quantity_value=0.75,
                quantity_unit="cup",
                prep={"method": "packed"},
                is_optional=False,
            ),
            IngredientIn(
                name="granulated sugar",
                quantity_value=0.75,
                quantity_unit="cup",
                is_optional=False,
            ),
            IngredientIn(
                name="large eggs",
                quantity_value=2.0,
                quantity_unit="pieces",
                is_optional=False,
            ),
            IngredientIn(
                name="vanilla extract",
                quantity_value=2.0,
                quantity_unit="teaspoons",
                is_optional=False,
            ),
            IngredientIn(
                name="chocolate chips",
                quantity_value=2.0,
                quantity_unit="cups",
                is_optional=False,
            ),
        ],
        confidence_score=0.96,
        extraction_notes=(
            "Excellent extraction quality with clear structure, precise "
            "measurements, and well-defined instructions. Recipe appears "
            "complete and ready to use."
        ),
        link_source="https://example.com/classic-chocolate-chip-cookies",
    )


@pytest.fixture
def complex_recipe_extraction():
    """RecipeExtractionResult with many ingredients and complex data using TestModel."""
    # Use TestModel to generate a realistic complex recipe
    test_model = TestModel(RecipeExtractionResult)

    return test_model.generate(
        title="Coq au Vin",
        description=(
            "A classic French country dish featuring chicken braised in red "
            "wine with mushrooms, pearl onions, and lardons"
        ),
        prep_time_minutes=45,
        cook_time_minutes=90,
        serving_min=6,
        serving_max=8,
        instructions=[
            "Cut chicken into serving pieces and season with salt and pepper",
            "Cook lardons in Dutch oven until crispy, then remove",
            "Brown chicken pieces in bacon fat until golden on all sides",
            "Remove chicken and sauté carrots, onions, and garlic",
            "Add tomato paste and cook until fragrant",
            "Deglaze with cognac and red wine, scraping up browned bits",
            "Return chicken and lardons to pot, add bouquet garni",
            "Simmer gently for 45 minutes until chicken is tender",
            "Sauté mushrooms and pearl onions separately",
            "Add mushrooms and onions to chicken, cook 15 more minutes",
            "Remove bouquet garni and adjust seasoning",
            "Serve hot with crusty bread",
        ],
        difficulty=RecipeDifficulty.HARD,
        category=RecipeCategory.DINNER,
        ingredients=[
            IngredientIn(
                name="whole chicken",
                quantity_value=1.0,
                quantity_unit="pieces",
                prep={"method": "cut into pieces"},
                is_optional=False,
            ),
            IngredientIn(
                name="thick-cut bacon",
                quantity_value=4.0,
                quantity_unit="ounces",
                prep={"method": "cut into lardons"},
                is_optional=False,
            ),
            IngredientIn(
                name="dry red wine",
                quantity_value=2.0,
                quantity_unit="cups",
                is_optional=False,
            ),
            IngredientIn(
                name="cognac",
                quantity_value=0.25,
                quantity_unit="cup",
                is_optional=False,
            ),
            IngredientIn(
                name="button mushrooms",
                quantity_value=8.0,
                quantity_unit="ounces",
                prep={"method": "quartered"},
                is_optional=False,
            ),
            IngredientIn(
                name="pearl onions",
                quantity_value=8.0,
                quantity_unit="ounces",
                prep={"method": "peeled"},
                is_optional=False,
            ),
            IngredientIn(
                name="carrots",
                quantity_value=2.0,
                quantity_unit="pieces",
                prep={"method": "sliced"},
                is_optional=False,
            ),
            IngredientIn(
                name="yellow onion",
                quantity_value=1.0,
                quantity_unit="pieces",
                prep={"method": "diced"},
                is_optional=False,
            ),
            IngredientIn(
                name="garlic cloves",
                quantity_value=3.0,
                quantity_unit="pieces",
                prep={"method": "minced"},
                is_optional=False,
            ),
            IngredientIn(
                name="tomato paste",
                quantity_value=2.0,
                quantity_unit="tablespoons",
                is_optional=False,
            ),
        ],
        ethnicity="french",
        oven_temperature_f=None,  # No oven needed for this stovetop dish
        confidence_score=0.92,
        extraction_notes=(
            "Complex recipe with multiple cooking techniques and precise "
            "timing. All ingredients properly quantified and prepared."
        ),
        link_source="https://example.com/authentic-coq-au-vin",
    )


@pytest.fixture
def breakfast_recipe_extraction():
    """RecipeExtractionResult for breakfast category using TestModel."""
    # Use TestModel to generate a realistic breakfast recipe
    test_model = TestModel(RecipeExtractionResult)

    return test_model.generate(
        title="Fluffy Scrambled Eggs",
        description=(
            "Light, fluffy scrambled eggs with fresh herbs - the perfect start "
            "to your day"
        ),
        prep_time_minutes=5,
        cook_time_minutes=8,
        serving_min=2,
        serving_max=4,
        instructions=[
            "Crack eggs into a bowl and whisk until well beaten",
            "Season with salt and pepper to taste",
            "Heat butter in non-stick pan over medium-low heat",
            "Pour eggs into pan and let sit for 30 seconds",
            "Gently stir with spatula, folding eggs as they cook",
            "Remove from heat when just set but still creamy",
            "Fold in fresh herbs and serve immediately",
        ],
        difficulty=RecipeDifficulty.EASY,
        category=RecipeCategory.BREAKFAST,
        ingredients=[
            IngredientIn(
                name="large eggs",
                quantity_value=4.0,
                quantity_unit="pieces",
                is_optional=False,
            ),
            IngredientIn(
                name="butter",
                quantity_value=1.0,
                quantity_unit="tablespoon",
                is_optional=False,
            ),
            IngredientIn(
                name="fresh chives",
                quantity_value=1.0,
                quantity_unit="tablespoon",
                prep={"method": "chopped"},
                is_optional=True,
            ),
            IngredientIn(
                name="fresh parsley",
                quantity_value=1.0,
                quantity_unit="tablespoon",
                prep={"method": "chopped"},
                is_optional=True,
            ),
        ],
        confidence_score=0.94,
        extraction_notes=(
            "Simple but perfectly executed breakfast recipe with clear "
            "technique for fluffy eggs."
        ),
        link_source="https://example.com/perfect-scrambled-eggs",
    )


@pytest.fixture
def dessert_recipe_extraction():
    """RecipeExtractionResult for dessert category using TestModel."""
    # Use TestModel to generate a realistic dessert recipe
    test_model = TestModel(RecipeExtractionResult)

    return test_model.generate(
        title="Classic Tiramisu",
        description=(
            "Rich and creamy Italian dessert with coffee-soaked ladyfingers "
            "and mascarpone cream"
        ),
        prep_time_minutes=30,
        cook_time_minutes=0,  # No cooking required
        serving_min=8,
        serving_max=10,
        instructions=[
            "Brew strong coffee and let cool to room temperature",
            "Mix coffee with coffee liqueur in shallow dish",
            "Beat egg yolks with sugar until pale and thick",
            "Fold in mascarpone cheese until smooth and creamy",
            "Beat egg whites to stiff peaks, then fold into mascarpone mixture",
            "Dip ladyfingers quickly in coffee mixture",
            "Arrange soaked ladyfingers in bottom of 8x8 dish",
            "Spread half mascarpone mixture over ladyfingers",
            "Add another layer of soaked ladyfingers",
            "Top with remaining mascarpone mixture",
            "Dust generously with cocoa powder",
            "Refrigerate at least 4 hours or overnight before serving",
        ],
        difficulty=RecipeDifficulty.MEDIUM,
        category=RecipeCategory.DESSERT,
        ingredients=[
            IngredientIn(
                name="mascarpone cheese",
                quantity_value=16.0,
                quantity_unit="ounces",
                prep={"method": "softened"},
                is_optional=False,
            ),
            IngredientIn(
                name="ladyfingers",
                quantity_value=24.0,
                quantity_unit="pieces",
                is_optional=False,
            ),
            IngredientIn(
                name="strong coffee",
                quantity_value=1.5,
                quantity_unit="cups",
                prep={"method": "cooled"},
                is_optional=False,
            ),
            IngredientIn(
                name="coffee liqueur",
                quantity_value=0.25,
                quantity_unit="cup",
                is_optional=True,
            ),
            IngredientIn(
                name="large egg yolks",
                quantity_value=4.0,
                quantity_unit="pieces",
                is_optional=False,
            ),
            IngredientIn(
                name="large egg whites",
                quantity_value=4.0,
                quantity_unit="pieces",
                is_optional=False,
            ),
            IngredientIn(
                name="granulated sugar",
                quantity_value=0.5,
                quantity_unit="cup",
                is_optional=False,
            ),
            IngredientIn(
                name="unsweetened cocoa powder",
                quantity_value=2.0,
                quantity_unit="tablespoons",
                is_optional=False,
            ),
        ],
        ethnicity="italian",
        confidence_score=0.91,
        extraction_notes=(
            "Authentic Italian dessert recipe with proper technique and "
            "traditional ingredients. No oven temperature needed as this is "
            "a no-bake recipe."
        ),
        link_source="https://example.com/authentic-tiramisu",
    )


# ============================================================================
# URL AND REQUEST FIXTURES
# ============================================================================


@pytest.fixture
def valid_recipe_url():
    """Valid recipe URL for testing."""
    return "https://example.com/recipe"


@pytest.fixture
def invalid_url():
    """Invalid URL for testing validation."""
    return "not-a-valid-url"


@pytest.fixture
def recipe_from_url_request():
    """Standard AIRecipeFromUrlRequest."""
    return AIRecipeFromUrlRequest(
        source_url="https://example.com/recipe",
        prompt_override="Custom extraction prompt",
    )


@pytest.fixture
def recipe_from_url_request_minimal():
    """Minimal AIRecipeFromUrlRequest without prompt override."""
    return AIRecipeFromUrlRequest(source_url="https://example.com/recipe")


# ============================================================================
# SSE EVENT FIXTURES
# ============================================================================


@pytest.fixture
def sse_started_event():
    """Standard SSE started event."""
    return {
        "status": "started",
        "step": "started",
        "progress": 0.0,
        "detail": "Starting recipe extraction",
    }


@pytest.fixture
def sse_fetching_event():
    """Standard SSE fetching event."""
    return {
        "status": "fetching",
        "step": "fetch_html",
        "progress": 0.2,
        "detail": "Fetching HTML content",
    }


@pytest.fixture
def sse_complete_event():
    """Standard SSE complete event."""
    return {
        "status": "complete",
        "step": "complete",
        "progress": 1.0,
        "success": True,
        "detail": "Recipe extraction completed successfully",
        "draft_id": str(uuid4()),
        "signed_url": "https://example.com/draft/test-token",
        "confidence_score": 0.85,
    }


@pytest.fixture
def sse_error_event():
    """Standard SSE error event."""
    return {
        "status": "error",
        "step": "ai_call",
        "progress": 1.0,
        "detail": "AI agent failure",
        "error_type": "agent_error",
    }
