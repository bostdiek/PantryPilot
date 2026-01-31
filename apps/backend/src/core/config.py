"""Application settings and CORS configuration."""

import json
import os
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env"),
        env_file_encoding="utf-8",
        extra="ignore",  # Allow extra env vars not defined in Settings
    )

    # App
    APP_NAME: str = "PantryPilot"
    ENVIRONMENT: str = "development"  # development | production | test

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # in minutes

    # CORS
    # Accept list or CSV/JSON string from env; normalized to list[str] by validators
    CORS_ORIGINS: list[str] | str = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    ALLOW_CREDENTIALS: bool = True

    # AI / LLM Provider Configuration (model-agnostic)
    # LLM_PROVIDER: "gemini" or "azure_openai" - selects which provider to use
    LLM_PROVIDER: Literal["gemini", "azure_openai"] = "gemini"

    # Model names - generic names that apply to either provider
    # These are used by the model factory to select the appropriate model
    CHAT_MODEL: str = "gemini-2.5-flash"  # General chat/completion model
    MULTIMODAL_MODEL: str = "gemini-2.5-flash-lite"  # Image/vision tasks
    EMBEDDING_MODEL: str = "gemini-embedding-001"  # Semantic embeddings
    TEXT_MODEL: str = "gemini-2.5-flash-lite"  # Fast text tasks (context gen)

    # Provider-specific API credentials
    # Gemini configuration
    GEMINI_API_KEY: str | None = None

    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_API_VERSION: str = "2024-10-01-preview"

    # External tool providers
    BRAVE_SEARCH_API_KEY: str | None = None

    # Azure Communication Services for email
    AZURE_COMMUNICATION_CONNECTION_STRING: str | None = None
    EMAIL_SENDER_ADDRESS: str = "DoNotReply@notify.pantrypilot.com"

    # Frontend URL for email links (verification, password reset)
    FRONTEND_URL: str = "http://localhost:5173"

    # Upstash Rate Limiting
    # REST URL and token for Upstash Redis; optional in development/test
    UPSTASH_REDIS_REST_URL: str | None = None
    UPSTASH_REDIS_REST_TOKEN: str | None = None

    # Rate limit settings (requests per window)
    # Default: 10 requests per 60 seconds - conservative to prevent abuse.
    # For production with higher traffic, increase via environment variables:
    #   RATE_LIMIT_REQUESTS=100 RATE_LIMIT_WINDOW_SECONDS=60
    # Auth endpoints benefit from stricter limits (brute-force protection).
    # AI endpoints benefit from moderate limits (cost protection).
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Observability / Telemetry
    # Enable Azure Monitor / Application Insights integration via OpenTelemetry.
    # Set ENABLE_OBSERVABILITY=true and provide APPLICATIONINSIGHTS_CONNECTION_STRING.
    # For local development, Logfire can be used as optional dev tooling.
    ENABLE_OBSERVABILITY: bool = False
    APPLICATIONINSIGHTS_CONNECTION_STRING: str | None = None
    OTEL_SERVICE_NAME: str = "pantrypilot-backend"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: object) -> list[str]:
        """Allow list, CSV string, or JSON array string for CORS origins."""
        if isinstance(v, list):
            return [str(i).strip() for i in v]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                try:
                    parsed = json.loads(s)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        "CORS_ORIGINS must be a CSV list or JSON array string"
                    ) from e
                if not isinstance(parsed, list):
                    raise ValueError("CORS_ORIGINS JSON must be a list")
                return [str(i).strip() for i in parsed]
            # CSV fallback
            return [i.strip() for i in s.split(",") if i.strip()]
        raise ValueError("Invalid CORS_ORIGINS type; expected str or list[str]")

    @model_validator(mode="after")
    def _validate_cors_credentials(self) -> "Settings":
        """Ensure wildcard origins are not used when credentials are allowed."""
        # Normalize in case the union allows a stray string at runtime
        if isinstance(self.CORS_ORIGINS, str):
            self.CORS_ORIGINS = self.assemble_cors_origins(self.CORS_ORIGINS)
        if self.ALLOW_CREDENTIALS and any(
            o.strip() == "*" for o in (self.CORS_ORIGINS or [])
        ):
            raise ValueError(
                "CORS configuration error: ALLOW_CREDENTIALS=True but "
                "CORS_ORIGINS contains '*'. Use explicit origins when credentials "
                "are allowed."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    env = os.getenv("ENVIRONMENT", "development").lower()
    if env not in {"development", "production", "test"}:
        raise ValueError("ENVIRONMENT must be 'development', 'production', or 'test'")

    if env == "production":
        env_file = ".env.prod"
    elif env == "development":
        env_file = ".env.dev"
    else:
        # test environment - no env file needed, use defaults
        env_file = ""
    # pydantic-settings supports _env_file at runtime; mypy doesn't type it.
    # For production, fail fast if SECRET_KEY is not provided.
    if env_file and not os.path.exists(env_file):  # pragma: no cover - defensive
        # Only provide a dev fallback in non-production environments
        if env == "development":
            os.environ.setdefault("SECRET_KEY", "dev-test-secret")
    # If we're in production, ensure SECRET_KEY is set and not the dev default
    if env == "production":
        sec = os.getenv("SECRET_KEY")
        if not sec or sec == "dev-test-secret":
            raise RuntimeError("SECRET_KEY must be set to a secure value in production")

    # The Settings initializer accepts a runtime-only `_env_file` kwarg used by
    # pydantic-settings; mypy's stub doesn't allow this call argument. The
    # ignore is scoped to the specific `call-arg` error to avoid hiding other
    # issues.
    return Settings(_env_file=env_file)  # type: ignore[call-arg]
