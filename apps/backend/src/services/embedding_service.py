"""Generate and manage recipe embeddings using Gemini Embeddings API."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np
from google import genai
from google.genai import types

from services.context_generator import generate_recipe_context


if TYPE_CHECKING:
    from models.recipes_names import Recipe

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768


@lru_cache
def get_embedding_client() -> genai.Client:
    """Get cached Gemini client."""
    return genai.Client()


def generate_recipe_text(recipe: Recipe) -> str:
    """Generate full text representation of recipe for embedding.

    Combines title, description, ingredients, and instructions into
    a coherent text block optimized for semantic understanding.
    """
    parts = [f"Recipe: {recipe.name}"]

    _add_basic_info(parts, recipe)
    _add_timing_info(parts, recipe)
    _add_ingredient_list(parts, recipe)
    _add_instruction_text(parts, recipe)

    return "\n".join(parts)


def _add_basic_info(parts: list[str], recipe: Recipe) -> None:
    """Add basic recipe information to parts list."""
    if recipe.description:
        parts.append(str(recipe.description))
    if recipe.ethnicity:
        parts.append(f"Cuisine: {str(recipe.ethnicity)}")
    if recipe.course_type:
        parts.append(f"Course: {str(recipe.course_type)}")
    if recipe.difficulty:
        parts.append(f"Difficulty: {str(recipe.difficulty)}")


def _add_timing_info(parts: list[str], recipe: Recipe) -> None:
    """Add cooking time information to parts list."""
    times = []
    if recipe.prep_time_minutes:
        times.append(f"{recipe.prep_time_minutes} min prep")
    if recipe.cook_time_minutes:
        times.append(f"{recipe.cook_time_minutes} min cook")
    if times:
        parts.append(f"Time: {', '.join(times)}")


def _add_ingredient_list(parts: list[str], recipe: Recipe) -> None:
    """Add ingredients to parts list."""
    if recipe.recipeingredients:
        ingredient_names = [
            ri.ingredient.ingredient_name
            for ri in recipe.recipeingredients
            if ri.ingredient
        ]
        if ingredient_names:
            parts.append(f"Ingredients: {', '.join(ingredient_names)}")


def _add_instruction_text(parts: list[str], recipe: Recipe) -> None:
    """Add cooking instructions to parts list."""
    if recipe.instructions:
        parts.append("Instructions: " + " ".join(recipe.instructions))


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding for text using Gemini API.

    Uses RETRIEVAL_DOCUMENT task type for recipe storage.
    Returns normalized 768-dimension vector.
    """
    client = get_embedding_client()

    result = await client.aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )

    if not result.embeddings:
        raise ValueError("No embeddings returned from API")

    # Normalize for cosine similarity (required for 768 dimensions)
    embedding = np.array(result.embeddings[0].values)
    normalized = embedding / np.linalg.norm(embedding)

    return list(normalized.tolist())


async def generate_query_embedding(query: str) -> list[float]:
    """Generate embedding for search query.

    Uses RETRIEVAL_QUERY task type optimized for search.
    """
    client = get_embedding_client()

    result = await client.aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )

    if not result.embeddings:
        raise ValueError("No embeddings returned from API")

    embedding = np.array(result.embeddings[0].values)
    normalized = embedding / np.linalg.norm(embedding)

    return list(normalized.tolist())


async def generate_recipe_embedding(recipe: Recipe) -> tuple[str, list[float]]:
    """Generate contextual embedding for a recipe.

    Follows Anthropic's Contextual Retrieval methodology:
    1. Generate contextual prefix using Flash-Lite
    2. Generate full recipe text
    3. Combine context + content for embedding
    4. Return both context and embedding for storage

    Returns:
        Tuple of (context, embedding_vector)
    """
    # 1. Generate contextual prefix using Flash-Lite
    context = await generate_recipe_context(recipe)

    # 2. Generate full recipe text
    recipe_text = generate_recipe_text(recipe)

    # 3. Combine context + content for embedding
    full_text = f"{context}\n\n{recipe_text}"

    # 4. Generate embedding using Gemini Embeddings
    embedding = await generate_embedding(full_text)

    return context, embedding
