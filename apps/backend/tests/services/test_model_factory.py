"""Tests for the centralized AI model factory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai import models


# Block any real model requests in tests
models.ALLOW_MODEL_REQUESTS = False


class TestIsAzureProvider:
    """Tests for _is_azure_provider function."""

    @patch("services.ai.model_factory.get_settings")
    def test_returns_true_when_azure_openai(self, mock_settings: MagicMock) -> None:
        """Test returns True when LLM_PROVIDER is azure_openai."""
        mock_settings.return_value.LLM_PROVIDER = "azure_openai"

        from services.ai.model_factory import _is_azure_provider

        assert _is_azure_provider() is True

    @patch("services.ai.model_factory.get_settings")
    def test_returns_false_when_gemini(self, mock_settings: MagicMock) -> None:
        """Test returns False when LLM_PROVIDER is not azure_openai."""
        mock_settings.return_value.LLM_PROVIDER = "gemini"

        from services.ai.model_factory import _is_azure_provider

        assert _is_azure_provider() is False


class TestValidateAzureCredentials:
    """Tests for _validate_azure_credentials function."""

    @patch("services.ai.model_factory.get_settings")
    def test_returns_true_with_valid_credentials(
        self, mock_settings: MagicMock
    ) -> None:
        """Test returns True when Azure credentials are configured."""
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = (
            "https://test.openai.azure.com"
        )
        mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"

        from services.ai.model_factory import _validate_azure_credentials

        assert _validate_azure_credentials() is True

    @patch("services.ai.model_factory.get_settings")
    def test_returns_false_with_missing_endpoint(
        self, mock_settings: MagicMock
    ) -> None:
        """Test returns False when endpoint is missing."""
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = None
        mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"

        from services.ai.model_factory import _validate_azure_credentials

        assert _validate_azure_credentials() is False

    @patch("services.ai.model_factory.get_settings")
    def test_returns_false_with_missing_api_key(self, mock_settings: MagicMock) -> None:
        """Test returns False when API key is missing."""
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = (
            "https://test.openai.azure.com"
        )
        mock_settings.return_value.AZURE_OPENAI_API_KEY = None

        from services.ai.model_factory import _validate_azure_credentials

        assert _validate_azure_credentials() is False

    @patch("services.ai.model_factory.get_settings")
    def test_logs_warning_on_missing_credentials(
        self, mock_settings: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logs warning when credentials are missing."""
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = None
        mock_settings.return_value.AZURE_OPENAI_API_KEY = None

        from services.ai.model_factory import _validate_azure_credentials

        _validate_azure_credentials()
        assert "credentials missing" in caplog.text.lower()


class TestValidateGeminiCredentials:
    """Tests for _validate_gemini_credentials function."""

    @patch("services.ai.model_factory.get_settings")
    def test_returns_true_with_api_key(self, mock_settings: MagicMock) -> None:
        """Test returns True when Gemini API key is configured."""
        mock_settings.return_value.GEMINI_API_KEY = "test-gemini-key"

        from services.ai.model_factory import _validate_gemini_credentials

        assert _validate_gemini_credentials() is True

    @patch("services.ai.model_factory.get_settings")
    def test_returns_false_without_api_key(self, mock_settings: MagicMock) -> None:
        """Test returns False when Gemini API key is missing."""
        mock_settings.return_value.GEMINI_API_KEY = None

        from services.ai.model_factory import _validate_gemini_credentials

        assert _validate_gemini_credentials() is False

    @patch("services.ai.model_factory.get_settings")
    def test_logs_warning_on_missing_key(
        self, mock_settings: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logs warning when API key is missing."""
        mock_settings.return_value.GEMINI_API_KEY = None

        from services.ai.model_factory import _validate_gemini_credentials

        _validate_gemini_credentials()
        assert "not configured" in caplog.text.lower()


class TestGetChatModel:
    """Tests for get_chat_model function."""

    @patch("services.ai.model_factory._validate_azure_credentials")
    @patch("services.ai.model_factory._is_azure_provider")
    @patch("services.ai.model_factory.get_settings")
    def test_returns_azure_model_when_configured(
        self,
        mock_settings: MagicMock,
        mock_is_azure: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Test returns Azure model when provider is azure_openai."""
        mock_is_azure.return_value = True
        mock_validate.return_value = True
        mock_settings.return_value.CHAT_MODEL = "gpt-4"
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = (
            "https://test.openai.azure.com"
        )
        mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"

        from services.ai.model_factory import get_chat_model

        model = get_chat_model()
        assert model is not None
        # Azure model is OpenAIModel type
        assert "OpenAI" in type(model).__name__

    @patch("services.ai.model_factory._validate_azure_credentials")
    @patch("services.ai.model_factory._is_azure_provider")
    @patch("services.ai.model_factory.get_settings")
    def test_returns_gemini_model_when_azure_not_configured(
        self,
        mock_settings: MagicMock,
        mock_is_azure: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Test returns Gemini model when Azure is not configured."""
        mock_is_azure.return_value = False
        mock_settings.return_value.CHAT_MODEL = "gemini-2.0-flash-exp"
        mock_settings.return_value.GEMINI_API_KEY = "test-gemini-key"

        from services.ai.model_factory import get_chat_model

        model = get_chat_model()
        assert model is not None
        # Gemini model is GoogleModel type
        assert "Google" in type(model).__name__

    @patch("services.ai.model_factory._validate_azure_credentials")
    @patch("services.ai.model_factory._is_azure_provider")
    @patch("services.ai.model_factory.get_settings")
    def test_falls_back_to_gemini_on_invalid_azure_credentials(
        self,
        mock_settings: MagicMock,
        mock_is_azure: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Test falls back to Gemini when Azure credentials are invalid."""
        mock_is_azure.return_value = True
        mock_validate.return_value = False
        mock_settings.return_value.CHAT_MODEL = "gemini-2.0-flash-exp"
        mock_settings.return_value.GEMINI_API_KEY = "test-gemini-key"

        from services.ai.model_factory import get_chat_model

        model = get_chat_model()
        assert model is not None
        # Falls back to Gemini model
        assert "Google" in type(model).__name__


class TestGetMultimodalModel:
    """Tests for get_multimodal_model function."""

    @patch("services.ai.model_factory._validate_azure_credentials")
    @patch("services.ai.model_factory._is_azure_provider")
    @patch("services.ai.model_factory.get_settings")
    def test_returns_azure_model_when_configured(
        self,
        mock_settings: MagicMock,
        mock_is_azure: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Test returns Azure model for multimodal tasks."""
        mock_is_azure.return_value = True
        mock_validate.return_value = True
        mock_settings.return_value.MULTIMODAL_MODEL = "gpt-4-vision"
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = (
            "https://test.openai.azure.com"
        )
        mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"

        from services.ai.model_factory import get_multimodal_model

        model = get_multimodal_model()
        assert model is not None

    @patch("services.ai.model_factory._validate_azure_credentials")
    @patch("services.ai.model_factory._is_azure_provider")
    @patch("services.ai.model_factory.get_settings")
    def test_returns_gemini_model_when_not_azure(
        self,
        mock_settings: MagicMock,
        mock_is_azure: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Test returns Gemini model for multimodal tasks."""
        mock_is_azure.return_value = False
        mock_settings.return_value.MULTIMODAL_MODEL = "gemini-2.0-flash-exp"
        mock_settings.return_value.GEMINI_API_KEY = "test-gemini-key"

        from services.ai.model_factory import get_multimodal_model

        model = get_multimodal_model()
        assert model is not None


class TestGetTextModel:
    """Tests for get_text_model function."""

    @patch("services.ai.model_factory._validate_azure_credentials")
    @patch("services.ai.model_factory._is_azure_provider")
    @patch("services.ai.model_factory.get_settings")
    def test_returns_azure_model_when_configured(
        self,
        mock_settings: MagicMock,
        mock_is_azure: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Test returns Azure model for text tasks."""
        mock_is_azure.return_value = True
        mock_validate.return_value = True
        mock_settings.return_value.TEXT_MODEL = "gpt-35-turbo"
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = (
            "https://test.openai.azure.com"
        )
        mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"

        from services.ai.model_factory import get_text_model

        model = get_text_model()
        assert model is not None

    @patch("services.ai.model_factory._validate_azure_credentials")
    @patch("services.ai.model_factory._is_azure_provider")
    @patch("services.ai.model_factory.get_settings")
    def test_returns_gemini_model_when_not_azure(
        self,
        mock_settings: MagicMock,
        mock_is_azure: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Test returns Gemini model for text tasks."""
        mock_is_azure.return_value = False
        mock_settings.return_value.TEXT_MODEL = "gemini-1.5-flash-8b"
        mock_settings.return_value.GEMINI_API_KEY = "test-gemini-key"

        from services.ai.model_factory import get_text_model

        model = get_text_model()
        assert model is not None


class TestGetEmbeddingClient:
    """Tests for get_embedding_client function."""

    @patch("services.ai.model_factory._validate_azure_credentials")
    @patch("services.ai.model_factory._is_azure_provider")
    @patch("services.ai.model_factory.get_settings")
    def test_returns_azure_client_when_configured(
        self,
        mock_settings: MagicMock,
        mock_is_azure: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Test returns Azure OpenAI client for embeddings."""
        from services.ai.model_factory import clear_embedding_client_cache

        clear_embedding_client_cache()  # Clear cache before test

        mock_is_azure.return_value = True
        mock_validate.return_value = True
        mock_settings.return_value.EMBEDDING_MODEL = "text-embedding-3-small"
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = (
            "https://test.openai.azure.com"
        )
        mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"
        mock_settings.return_value.AZURE_OPENAI_API_VERSION = "2024-02-15-preview"

        from services.ai.model_factory import get_embedding_client

        client = get_embedding_client()
        assert client is not None
        assert "AsyncAzureOpenAI" in str(type(client))

    @patch("services.ai.model_factory._validate_azure_credentials")
    @patch("services.ai.model_factory._is_azure_provider")
    @patch("services.ai.model_factory.get_settings")
    def test_returns_gemini_client_when_not_azure(
        self,
        mock_settings: MagicMock,
        mock_is_azure: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Test returns Gemini client for embeddings."""
        from services.ai.model_factory import clear_embedding_client_cache

        clear_embedding_client_cache()  # Clear cache before test

        mock_is_azure.return_value = False
        mock_settings.return_value.EMBEDDING_MODEL = "text-embedding-004"
        mock_settings.return_value.GEMINI_API_KEY = "test-gemini-key"

        from services.ai.model_factory import get_embedding_client

        client = get_embedding_client()
        assert client is not None
        assert "Client" in str(type(client))

    @patch("services.ai.model_factory._validate_azure_credentials")
    @patch("services.ai.model_factory._is_azure_provider")
    @patch("services.ai.model_factory.get_settings")
    def test_caches_client_on_multiple_calls(
        self,
        mock_settings: MagicMock,
        mock_is_azure: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Test client is cached and reused."""
        from services.ai.model_factory import clear_embedding_client_cache

        clear_embedding_client_cache()  # Clear cache before test

        mock_is_azure.return_value = False
        mock_settings.return_value.EMBEDDING_MODEL = "text-embedding-004"
        mock_settings.return_value.GEMINI_API_KEY = "test-gemini-key"

        from services.ai.model_factory import get_embedding_client

        client1 = get_embedding_client()
        client2 = get_embedding_client()
        assert client1 is client2  # Same instance due to caching


class TestGetCurrentEmbeddingModelName:
    """Tests for get_current_embedding_model_name function."""

    @patch("services.ai.model_factory.get_settings")
    def test_returns_embedding_model_name(self, mock_settings: MagicMock) -> None:
        """Test returns configured embedding model name."""
        mock_settings.return_value.EMBEDDING_MODEL = "text-embedding-004"

        from services.ai.model_factory import get_current_embedding_model_name

        assert get_current_embedding_model_name() == "text-embedding-004"


class TestClearEmbeddingClientCache:
    """Tests for clear_embedding_client_cache function."""

    @patch("services.ai.model_factory._validate_azure_credentials")
    @patch("services.ai.model_factory._is_azure_provider")
    @patch("services.ai.model_factory.get_settings")
    def test_clears_cached_client(
        self,
        mock_settings: MagicMock,
        mock_is_azure: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Test cache is cleared and new client is created."""
        from services.ai.model_factory import clear_embedding_client_cache

        clear_embedding_client_cache()

        mock_is_azure.return_value = False
        mock_settings.return_value.EMBEDDING_MODEL = "text-embedding-004"
        mock_settings.return_value.GEMINI_API_KEY = "test-gemini-key"

        from services.ai.model_factory import get_embedding_client

        client1 = get_embedding_client()
        clear_embedding_client_cache()
        client2 = get_embedding_client()

        # Different instances after cache clear
        assert client1 is not client2
