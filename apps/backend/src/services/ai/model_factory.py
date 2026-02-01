"""Centralized AI model factory for all LLM/embedding operations.

This module provides a single source of truth for creating AI models,
supporting both Gemini and Azure OpenAI providers based on configuration.

Usage:
    from services.ai.model_factory import (
        get_chat_model,
        get_multimodal_model,
        get_text_model,
        get_embedding_client,
    )

    model = get_chat_model()  # Returns pydantic-ai Model
    client = get_embedding_client()  # Returns provider-specific async client
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from core.config import get_settings


# OpenAI reasoning models that support reasoning_effort parameter
REASONING_MODELS = {
    "gpt-5-mini",
    "gpt-5-nano",
    "o1-mini",
    "o1-preview",
    "o1",
    "o3-mini",
}


if TYPE_CHECKING:
    from httpx import AsyncClient

logger = logging.getLogger(__name__)


def _normalize_azure_endpoint(endpoint: str) -> str:
    """Normalize Azure OpenAI endpoint.

    Azure endpoints are typically provided as `https://{resource}.openai.azure.com/`.
    Trailing slashes can lead to `//openai/...` URLs, which Azure may treat as a
    different path and return 404.
    """
    return endpoint.rstrip("/")


def _is_azure_provider() -> bool:
    """Check if Azure OpenAI should be used based on configuration."""
    settings = get_settings()
    return settings.LLM_PROVIDER == "azure_openai"


def _validate_azure_credentials() -> bool:
    """Validate that Azure OpenAI credentials are properly configured."""
    settings = get_settings()
    if (
        not settings.AZURE_OPENAI_ENDPOINT
        or not settings.AZURE_OPENAI_API_KEY
        or not settings.AZURE_OPENAI_API_VERSION
    ):
        logger.warning(
            "LLM_PROVIDER=azure_openai but credentials missing, falling back to Gemini"
        )
        return False
    return True


def _validate_gemini_credentials() -> bool:
    """Validate that Gemini API key is configured."""
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        logger.warning("Gemini API key not configured")
        return False
    return True


def _create_azure_model(
    model_name: str,
    http_client: AsyncClient | None = None,
) -> Model:
    """Create an Azure OpenAI model with the specified deployment name.

    For reasoning models (o1, o3, gpt-5 series), automatically applies
    low reasoning effort for faster, more cost-effective responses.
    """
    settings = get_settings()

    from openai import AsyncAzureOpenAI

    # AZURE_OPENAI_ENDPOINT is validated in _validate_azure_credentials
    azure_endpoint = _normalize_azure_endpoint(settings.AZURE_OPENAI_ENDPOINT or "")
    azure_client = AsyncAzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        http_client=http_client,
    )

    provider = OpenAIProvider(openai_client=azure_client)

    # Apply low reasoning effort for reasoning models
    if model_name in REASONING_MODELS:
        logger.info(f"Applying low reasoning effort for reasoning model: {model_name}")
        # reasoning_effort is a newer parameter not in TypedDict yet
        return OpenAIModel(  # type: ignore[call-overload,no-any-return]
            model_name,
            provider=provider,
            settings={"reasoning_effort": "low"},
        )

    return OpenAIModel(model_name, provider=provider)


def _create_gemini_model(
    model_name: str,
    http_client: AsyncClient | None = None,
) -> Model:
    """Create a Google Gemini model with the specified model name."""
    settings = get_settings()
    provider = GoogleProvider(
        api_key=settings.GEMINI_API_KEY,
        http_client=http_client,
    )
    return cast(Model, GoogleModel(model_name, provider=provider))


def get_chat_model(http_client: AsyncClient | None = None) -> Model:
    """Get the chat/completion model based on configuration.

    This model is suitable for general conversational AI tasks.

    Args:
        http_client: Optional HTTP client for custom retry logic.

    Returns:
        A pydantic-ai Model configured for the selected provider.
    """
    settings = get_settings()

    if _is_azure_provider() and _validate_azure_credentials():
        logger.info(f"Using Azure OpenAI chat model: {settings.CHAT_MODEL}")
        return _create_azure_model(settings.CHAT_MODEL, http_client)

    # Fallback to Gemini - validate credentials
    if not _validate_gemini_credentials():
        raise ValueError(
            "No valid LLM provider configured. Either set Azure OpenAI "
            "credentials (AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY) "
            "or Gemini credentials (GEMINI_API_KEY)."
        )

    logger.info(f"Using Gemini chat model: {settings.CHAT_MODEL}")
    return _create_gemini_model(settings.CHAT_MODEL, http_client)


def get_multimodal_model(http_client: AsyncClient | None = None) -> Model:
    """Get the multimodal model for image/vision tasks.

    This model supports image inputs for tasks like recipe extraction
    from photos.

    Args:
        http_client: Optional HTTP client for custom retry logic.

    Returns:
        A pydantic-ai Model configured for multimodal tasks.
    """
    settings = get_settings()

    if _is_azure_provider() and _validate_azure_credentials():
        logger.info(f"Using Azure OpenAI multimodal model: {settings.MULTIMODAL_MODEL}")
        return _create_azure_model(settings.MULTIMODAL_MODEL, http_client)

    # Fallback to Gemini - validate credentials
    if not _validate_gemini_credentials():
        raise ValueError(
            "No valid LLM provider configured. Either set Azure OpenAI "
            "credentials (AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY) "
            "or Gemini credentials (GEMINI_API_KEY)."
        )

    logger.info(f"Using Gemini multimodal model: {settings.MULTIMODAL_MODEL}")
    return _create_gemini_model(settings.MULTIMODAL_MODEL, http_client)


def get_text_model(http_client: AsyncClient | None = None) -> Model:
    """Get the text model for fast text tasks.

    This model is optimized for quick text operations like context
    generation, title generation, etc.

    Args:
        http_client: Optional HTTP client for custom retry logic.

    Returns:
        A pydantic-ai Model configured for text tasks.
    """
    settings = get_settings()

    if _is_azure_provider() and _validate_azure_credentials():
        logger.info(f"Using Azure OpenAI text model: {settings.TEXT_MODEL}")
        return _create_azure_model(settings.TEXT_MODEL, http_client)

    # Fallback to Gemini - validate credentials
    if not _validate_gemini_credentials():
        raise ValueError(
            "No valid LLM provider configured. Either set Azure OpenAI "
            "credentials (AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY) "
            "or Gemini credentials (GEMINI_API_KEY)."
        )

    logger.info(f"Using Gemini text model: {settings.TEXT_MODEL}")
    return _create_gemini_model(settings.TEXT_MODEL, http_client)


@lru_cache
def get_embedding_client() -> Any:
    """Get the cached embedding client for the configured provider.

    Returns an async client suitable for generating embeddings.
    For Azure: AsyncAzureOpenAI client
    For Gemini: google.genai.Client

    Returns:
        Provider-specific async embedding client.
    """
    settings = get_settings()

    if _is_azure_provider() and _validate_azure_credentials():
        from openai import AsyncAzureOpenAI

        logger.info(f"Using Azure OpenAI for embeddings: {settings.EMBEDDING_MODEL}")
        # AZURE_OPENAI_ENDPOINT is validated in _validate_azure_credentials
        return AsyncAzureOpenAI(
            azure_endpoint=_normalize_azure_endpoint(
                settings.AZURE_OPENAI_ENDPOINT or ""
            ),
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )

    # Fallback to Gemini - validate credentials
    if not _validate_gemini_credentials():
        raise ValueError(
            "No valid embedding provider configured. Either set Azure OpenAI "
            "credentials (AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY) "
            "or Gemini credentials (GEMINI_API_KEY)."
        )

    from google import genai

    logger.info(f"Using Gemini for embeddings: {settings.EMBEDDING_MODEL}")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def get_current_embedding_model_name() -> str:
    """Get the name of the currently configured embedding model.

    Returns:
        The model name string for the active embedding configuration.
    """
    return get_settings().EMBEDDING_MODEL


def clear_embedding_client_cache() -> None:
    """Clear the cached embedding client.

    Useful for testing or when configuration changes at runtime.
    """
    get_embedding_client.cache_clear()
