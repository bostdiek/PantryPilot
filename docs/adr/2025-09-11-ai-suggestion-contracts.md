# ADR 001: Defining Contracts for AI-Generated Meal Plan and Recipe Suggestions

## Status

Proposed

## Context

PantryPilot is an AI-assisted meal planning service where users can import or create recipes, set preferences and dietary constraints, and generate personalized weekly meal plans with grocery guidance. The backend uses FastAPI with Pydantic schemas for data validation and serialization, primarily in `apps/backend/src/schemas/` (e.g., `mealplans.py`, `recipes.py`, `user_preferences.py`). Existing models include `Recipe`, `MealHistory`, and `UserPreferences`, with API endpoints under `/api/v1/` for meal plans and recipes.

The introduction of AI-driven suggestions requires well-defined contracts to ensure seamless integration between the AI service (backend or external), the database, and the frontend (React). These contracts must handle inputs like user preferences, meal history, and constraints, and produce outputs such as suggested meal plans or generated recipes that can be persisted or displayed.

Key considerations:

- **Existing Structures**:
  - Meal plans use `WeeklyMealPlanOut` with `days` containing `DayPlanOut` (day of week, date, list of `MealEntryOut` including `recipe_id`, `meal_type` (currently only "dinner"), cooked status).
  - Recipes use `RecipeOut` with fields like `title`, `ingredients` (list of `IngredientOut`), `instructions`, `difficulty`, `category`, timings, and servings.
  - User preferences (`UserPreferencesResponse`) include `family_size`, `allergies`, `dietary_restrictions`, `preferred_cuisines`, etc.
- **AI Integration Needs**: AI suggestions should personalize based on user data (e.g., avoid allergies, favor cuisines) and history (e.g., avoid recent repeats). Outputs must map to existing DB models for persistence (e.g., save as draft meal plans or new recipes).
- **Challenges**: Ensure privacy (user-owned data, no cross-user training), handle AI variability (e.g., confidence scores, alternatives), support versioning, and manage errors (e.g., invalid inputs, AI failures).
- **Non-Goals**: This ADR focuses on data contracts (schemas, API formats); implementation details like AI model selection are out of scope.

## Decision

We will define Pydantic-based contracts for AI requests and responses, introducing new schemas in `apps/backend/src/schemas/ai.py`. These will extend existing ones where possible for compatibility. New API endpoints will be added under `/api/v1/ai/` (e.g., `POST /api/v1/ai/suggest-meal-plan`, `POST /api/v1/ai/suggest-recipe`).

### Proposed Schemas

All schemas will use `ConfigDict(extra="forbid")` for strict validation and include documentation via `Field(description=...)`.

#### Input Schemas

1. **AISuggestionRequest** (Base for both meal plan and recipe suggestions):

   ```python
   from datetime import date
   from typing import List, Dict, Any, Optional
   from uuid import UUID

   from pydantic import BaseModel, Field, ConfigDict

   class AISuggestionRequest(BaseModel):
       user_id: UUID = Field(..., description="Identifier of the user requesting suggestions")
       start_date: date = Field(..., description="Start date for the planning period (e.g., Sunday for weekly plans)")
       preferences: UserPreferencesResponse = Field(..., description="User's preferences and constraints")
       meal_history: Optional[List[MealHistoryOut]] = Field(default=None, description="Recent meal history to avoid repeats")
       user_recipes: Optional[List[RecipeOut]] = Field(default=None, description="User's existing recipes for basing suggestions")
       constraints: Optional[Dict[str, Any]] = Field(default=None, description="Additional constraints like budget or time limits")

       model_config = ConfigDict(extra="forbid")
   ```

2. **AIMealPlanRequest** (Extends `AISuggestionRequest`):

   ```python
   class AIMealPlanRequest(AISuggestionRequest):
       num_days: int = Field(default=7, ge=1, le=30, description="Number of days to plan")
       meals_per_day: int = Field(default=1, ge=1, le=3, description="Number of meals per day (e.g., 1 for dinner only)")
   ```

3. **AIRecipeSuggestionRequest** (Extends `AISuggestionRequest`):
   ```python
   class AIRecipeSuggestionRequest(AISuggestionRequest):
       prompt: Optional[str] = Field(default=None, description="Optional user prompt for recipe generation")
       base_on_recipe: Optional[RecipeOut] = Field(default=None, description="Optional base recipe to modify")
       category: Optional[RecipeCategory] = Field(default=None, description="Target category for the recipe")
   ```

#### Output Schemas

1. **AIMealSuggestion** (For individual meal entries):

   ```python
   from enum import Enum
   from typing import Literal

   class AIMealType(str, Enum):
       DINNER = "dinner"
       # Extend as needed: LUNCH = "lunch", etc.

   class AIMealSuggestion(BaseModel):
       planned_for_date: date = Field(..., description="Date for this meal")
       meal_type: AIMealType = Field(..., description="Type of meal")
       suggested_recipe: Optional[RecipeOut] = Field(default=None, description="Existing recipe suggestion")
       generated_recipe: Optional['AIGeneratedRecipe'] = Field(default=None, description="New AI-generated recipe")
       confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI confidence in this suggestion (0-1)")
       alternatives: List['AIRecipeSuggestion'] = Field(..., description="Alternative recipe options")
       rationale: str = Field(..., description="Brief explanation for the suggestion (e.g., 'Matches preferences')")
       estimated_prep_time: Optional[int] = Field(default=None, ge=0, description="Estimated prep time in minutes")

       model_config = ConfigDict(extra="forbid")
   ```

2. **AIDaySuggestion**:

   ```python
   class AIDaySuggestion(BaseModel):
       date: date = Field(..., description="Date for the day")
       day_of_week: Literal["Sunday", "Monday", ..., "Saturday"] = Field(..., description="Day label")
       entries: List[AIMealSuggestion] = Field(..., description="Meals for the day")

       model_config = ConfigDict(extra="forbid")
   ```

3. **AIMealPlanSuggestion**:

   ```python
   class AIMealPlanSuggestion(BaseModel):
       week_start_date: date = Field(..., description="Start date of the plan")
       days: List[AIDaySuggestion] = Field(..., min_length=1, description="Daily suggestions")
       overall_rationale: str = Field(..., description="High-level plan explanation")
       total_estimated_cost: Optional[float] = Field(default=None, description="Estimated total cost based on ingredients")
       grocery_guidance: Optional[str] = Field(default=None, description="Summary of required groceries")

       model_config = ConfigDict(extra="forbid")
   ```

4. **AIGeneratedRecipe** (Extends `RecipeCreate` for new recipes):

   ```python
   class AIGeneratedRecipe(RecipeCreate):
       is_ai_generated: bool = Field(default=True, description="Flag indicating AI origin")
       ai_confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence in generation")
       source_prompt: Optional[str] = Field(default=None, description="Prompt used for generation")
   ```

5. **AIRecipeSuggestion** (For alternatives or standalone suggestions):

   ```python
   class AIRecipeSuggestion(BaseModel):
       title: str = Field(..., min_length=1, description="Suggested recipe title")
       ingredients: List[IngredientOut] = Field(..., description="Ingredients list")
       instructions: List[str] = Field(..., min_length=1, description="Step-by-step instructions")
       estimated_prep_time: int = Field(..., ge=0, description="Estimated prep time")
       estimated_cook_time: int = Field(..., ge=0, description="Estimated cook time")
       difficulty: RecipeDifficulty = Field(..., description="Difficulty level")
       category: RecipeCategory = Field(..., description="Category")
       confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
       rationale: str = Field(..., description="Why this recipe fits")

       model_config = ConfigDict(extra="forbid")
   ```

6. **AIRecipeSuggestionResponse**:
   ```python
   class AIRecipeSuggestionResponse(BaseModel):
       generated_recipe: AIGeneratedRecipe = Field(..., description="Primary generated recipe")
       similar_existing: Optional[List[RecipeOut]] = Field(default=None, description="Similar user recipes")
       alternatives: List[AIRecipeSuggestion] = Field(..., description="Alternative suggestions")
   ```

#### API Contracts

- **POST /api/v1/ai/suggest-meal-plan**: Input `AIMealPlanRequest`, Output `AIMealPlanSuggestion` (wrapped in `ApiResponse`). Auth required (user_id from token).
- **POST /api/v1/ai/suggest-recipe**: Input `AIRecipeSuggestionRequest`, Output `AIRecipeSuggestionResponse`.
- Responses include confidence and rationale for transparency.
- Error Handling: Use standard FastAPI exceptions (e.g., `HTTPException(422)` for validation, `HTTPException(500)` for AI errors with `detail="AI generation failed"`).

#### Integration Points

- **Persistence**: Frontend/DB can map `AIMealPlanSuggestion` to `WeeklyMealPlanOut` by creating/saving recipes first (POST /recipes), then linking via `recipe_id`. Add `is_ai_generated: bool` to `Recipe` model/schema for flagging.
- **Versioning**: Schemas under v1; future changes via v2 endpoints.
- **Privacy**: All operations scoped to `user_id`; AI prompts anonymized (no PII beyond preferences/recipes).
- **Frontend Compatibility**: Outputs align with existing `RecipeOut` and `MealEntryOut` for easy rendering (e.g., `RecipeCard` component).

## Consequences

- **Positive**:

  - Enables robust AI integration without breaking existing APIs.
  - Ensures type safety and validation via Pydantic.
  - Supports personalization while maintaining user data ownership.
  - Provides extensibility (e.g., add nutrition estimates later).

- **Negative/Neutral**:

  - Requires schema updates and new models; minimal migration impact (add fields to existing tables via Alembic).
  - AI outputs may need post-processing (e.g., validate generated ingredients against standards).
  - Increases API surface; document in OpenAPI spec.
  - Potential for schema bloat; monitor and refactor if needed.

- **Risks**:
  - AI hallucination: Mitigated by confidence scores and user review before saving.
  - Performance: AI calls may be async; use background tasks if slow.
  - Cost: External AI usage; track via monitoring.

This ADR should be reviewed and approved before implementation in Code mode.
