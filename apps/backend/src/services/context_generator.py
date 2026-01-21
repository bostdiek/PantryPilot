"""Generate contextual prefixes for recipe embeddings using Gemini Flash-Lite."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from google import genai
from google.genai import types

from core.config import get_settings


if TYPE_CHECKING:
    from models.recipes_names import Recipe

logger = logging.getLogger(__name__)

# Use cheapest/fastest model for context generation
CONTEXT_MODEL = "gemini-2.0-flash-lite"
CONTEXT_MAX_TOKENS = 150  # ~2-3 sentences


RECIPE_CONTEXT_PROMPT = """You are a recipe search assistant.
Generate a brief context (1-3 sentences) that describes this recipe's
key searchable characteristics.

Include relevant details about:
- Cuisine type or ethnicity (Italian, Mexican, Asian, etc.)
- Meal category (breakfast, dinner, dessert, etc.)
- Main proteins or key ingredients
- Cooking style (quick weeknight, slow-cooked, grilled, baked, etc.)
- Dietary considerations if obvious (vegetarian, low-carb, etc.)
- Occasion or purpose (family dinner, meal prep, entertaining, etc.)
- Difficulty or time requirements
- Good for hot weather, grilling, cold weather, etc.

Recipe:
{recipe_content}

Context (1-3 sentences only):"""


class RecipeContextGenerator:
    """Generates contextual prefixes for recipe embeddings.

    Following Anthropic's Contextual Retrieval methodology, we prepend
    a short LLM-generated context to each recipe before embedding.
    This improves semantic search by 35% according to Anthropic's research.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize with optional API key override."""
        settings = get_settings()
        self._client = genai.Client(api_key=api_key or settings.GEMINI_API_KEY)
        self._model = CONTEXT_MODEL

    def _format_recipe_content(self, recipe: Recipe) -> str:
        """Format recipe into text for context generation."""
        parts = [f"Title: {recipe.name}"]

        self._add_description(parts, recipe)
        self._add_ingredients(parts, recipe)
        self._add_instructions(parts, recipe)
        self._add_times(parts, recipe)
        self._add_metadata(parts, recipe)

        return "\n".join(parts)

    def _add_description(self, parts: list[str], recipe: Recipe) -> None:
        """Add description to parts list."""
        if recipe.description:
            parts.append(f"Description: {recipe.description}")

    def _add_ingredients(self, parts: list[str], recipe: Recipe) -> None:
        """Add ingredients to parts list."""
        if recipe.recipeingredients:
            ingredient_names = [
                ri.ingredient.ingredient_name
                for ri in recipe.recipeingredients[:20]
                if ri.ingredient
            ]
            if ingredient_names:
                parts.append(f"Ingredients: {', '.join(ingredient_names)}")

    def _add_instructions(self, parts: list[str], recipe: Recipe) -> None:
        """Add instructions to parts list."""
        if recipe.instructions:
            steps = recipe.instructions[:10]  # First 10 steps for brevity
            parts.append(f"Instructions: {' '.join(steps)}")

    def _add_times(self, parts: list[str], recipe: Recipe) -> None:
        """Add cooking times to parts list."""
        time_parts = []
        if recipe.prep_time_minutes:
            time_parts.append(f"{recipe.prep_time_minutes} min prep")
        if recipe.cook_time_minutes:
            time_parts.append(f"{recipe.cook_time_minutes} min cook")
        if time_parts:
            parts.append(f"Time: {', '.join(time_parts)}")

    def _add_metadata(self, parts: list[str], recipe: Recipe) -> None:
        """Add recipe metadata to parts list."""
        if recipe.difficulty:
            parts.append(f"Difficulty: {recipe.difficulty}")
        if recipe.course_type:
            parts.append(f"Category: {recipe.course_type}")
        if recipe.ethnicity:
            parts.append(f"Cuisine: {recipe.ethnicity}")

    async def generate_context(self, recipe: Recipe) -> str:
        """Generate contextual prefix for a recipe.

        Returns:
            A 1-3 sentence context string to prepend before embedding.
        """
        recipe_content = self._format_recipe_content(recipe)
        prompt = RECIPE_CONTEXT_PROMPT.format(recipe_content=recipe_content)

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=CONTEXT_MAX_TOKENS,
                    temperature=0.3,  # Low temp for consistent output
                ),
            )
            if response.text is None:
                logger.warning(f"Empty response for '{recipe.name}'")
                return self._generate_fallback_context(recipe)
            context = response.text.strip()
            logger.debug(f"Generated context for '{recipe.name}': {context[:80]}...")
            return context

        except Exception as e:
            logger.warning(f"Failed to generate context for '{recipe.name}': {e}")
            return self._generate_fallback_context(recipe)

    def _generate_fallback_context(self, recipe: Recipe) -> str:
        """Generate basic context from metadata (no LLM call)."""
        parts = []

        if recipe.ethnicity:
            parts.append(f"This is a {recipe.ethnicity} recipe")
        else:
            parts.append("This recipe")

        if recipe.course_type:
            parts.append(f"for {recipe.course_type}")

        if recipe.difficulty:
            parts.append(f"with {recipe.difficulty} difficulty")

        parts.append(f"called {recipe.name}.")

        return " ".join(parts)


# Singleton instance
_context_generator: RecipeContextGenerator | None = None


def get_context_generator() -> RecipeContextGenerator:
    """Get or create the singleton context generator."""
    global _context_generator
    if _context_generator is None:
        _context_generator = RecipeContextGenerator()
    return _context_generator


async def generate_recipe_context(recipe: Recipe) -> str:
    """Convenience function to generate recipe context."""
    generator = get_context_generator()
    return await generator.generate_context(recipe)
