"""Generate and manage recipe embeddings using Gemini or Azure OpenAI APIs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from core.config import get_settings
from services.ai.model_factory import (
    get_current_embedding_model_name,
    get_embedding_client,
)
from services.context_generator import generate_recipe_context


if TYPE_CHECKING:
    from models.recipes_names import Recipe

logger = logging.getLogger(__name__)

# Embedding dimensions - consistent across both providers
# Azure text-embedding-3-small supports 768 dimensions, matching Gemini
EMBEDDING_DIMENSIONS = 768


def _is_azure_provider() -> bool:
    """Check if Azure OpenAI should be used for embeddings."""
    settings = get_settings()
    return settings.LLM_PROVIDER == "azure_openai"


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
    """Generate embedding for text using Gemini or Azure OpenAI API.

    Uses RETRIEVAL_DOCUMENT task type for recipe storage.
    Returns normalized 768-dimension vector.
    """
    if _is_azure_provider():
        return await _generate_azure_embedding(text)
    else:
        return await _generate_gemini_embedding(text, task_type="RETRIEVAL_DOCUMENT")


async def _generate_azure_embedding(text: str) -> list[float]:
    """Generate embedding using Azure OpenAI."""
    settings = get_settings()
    client = get_embedding_client()

    response = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS,
    )

    if not response.data:
        raise ValueError("No embeddings returned from Azure API")

    embedding = np.array(response.data[0].embedding)
    return _normalize_embedding(embedding, "document")


async def _generate_gemini_embedding(text: str, task_type: str) -> list[float]:
    """Generate embedding using Gemini API."""
    from google.genai import types

    settings = get_settings()
    client = get_embedding_client()

    result = await client.aio.models.embed_content(
        model=settings.EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )

    if not result.embeddings:
        raise ValueError("No embeddings returned from Gemini API")

    embedding = np.array(result.embeddings[0].values)
    return _normalize_embedding(embedding, "document")


def _normalize_embedding(embedding: np.ndarray, embed_type: str) -> list[float]:
    """Normalize embedding for cosine similarity."""
    norm = np.linalg.norm(embedding)

    if norm == 0:
        raise ValueError(
            f"{embed_type.capitalize()} embedding has zero norm (all zeros). "
            "Cannot normalize. This may indicate an issue with the input text "
            "or API response."
        )

    normalized = embedding / norm
    return list(normalized.tolist())


async def generate_query_embedding(query: str) -> list[float]:
    """Generate embedding for search query.

    Uses RETRIEVAL_QUERY task type optimized for search.
    Works with both Azure OpenAI and Gemini.
    """
    if _is_azure_provider():
        # Azure uses same embedding for both document and query
        return await _generate_azure_embedding(query)
    else:
        return await _generate_gemini_embedding(query, task_type="RETRIEVAL_QUERY")


async def generate_recipe_embedding(
    recipe: Recipe,
) -> tuple[str, list[float], str]:
    """Generate contextual embedding for a recipe.

    Follows Anthropic's Contextual Retrieval methodology:
    1. Generate contextual prefix using Flash-Lite
    2. Generate full recipe text
    3. Combine context + content for embedding
    4. Return context, embedding, and model name for storage

    Returns:
        Tuple of (context, embedding_vector, model_name)
    """
    # 1. Generate contextual prefix using Flash-Lite
    context = await generate_recipe_context(recipe)

    # 2. Generate full recipe text
    recipe_text = generate_recipe_text(recipe)

    # 3. Combine context + content for embedding
    full_text = f"{context}\n\n{recipe_text}"

    # 4. Generate embedding using configured embedding model
    embedding = await generate_embedding(full_text)

    # 5. Get the model name for tracking
    model_name = get_current_embedding_model_name()

    return context, embedding, model_name
