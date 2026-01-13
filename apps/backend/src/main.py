import logging
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from api.v1.api import api_router
from core.config import get_settings
from core.error_handler import (
    ExceptionNormalizationMiddleware,
    global_exception_handler,
    setup_logging,
)
from core.middleware import CorrelationIdMiddleware


settings = get_settings()

# Setup logging
setup_logging()


def validate_cors_origins(origins: list[str]) -> list[str]:
    """Validate and sanitize CORS origins provided as a list of strings."""

    validated_origins: list[str] = []

    def is_valid_url(url: str) -> bool:
        parsed = urlparse(url)
        return bool(parsed.scheme in {"http", "https"} and parsed.netloc)

    for origin in origins:
        candidate = origin.strip()
        if not candidate:
            continue
        if is_valid_url(candidate):
            validated_origins.append(candidate)
        else:
            logging.warning(f"Invalid CORS origin '{origin}' ignored")

    return validated_origins


app = FastAPI(
    title="SmartMealPlanner API",
    description="A smart pantry management system",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

# Add proxy headers middleware for Azure Container Apps / reverse proxy support
# This ensures redirects use HTTPS when behind a proxy that terminates TLS
if settings.ENVIRONMENT in ("development", "production"):  # pragma: no cover
    app.add_middleware(ProxyHeadersMiddleware)
    logging.info("ProxyHeadersMiddleware enabled for reverse proxy support")

# Add correlation ID middleware and final exception normalization safety net
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(ExceptionNormalizationMiddleware)

# Add global exception handler
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, global_exception_handler)

# Configure CORS - enabled for local development and test environments
# In production, CORS is handled by Azure Container Apps at the infrastructure level
if settings.ENVIRONMENT not in ("production",):
    origins = validate_cors_origins(settings.CORS_ORIGINS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=settings.ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logging.info(f"CORS middleware enabled for origins: {origins}")
else:  # pragma: no cover - production only
    logging.info("CORS middleware disabled - handled by Azure Container Apps")

# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Mount OpenAPI docs under /api/v1/docs and /api/v1/redoc
@app.get("/api/v1/docs", include_in_schema=False)
def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json", title="SmartMealPlanner API Docs"
    )


@app.get("/api/v1/redoc", include_in_schema=False)
def redoc_html():
    return get_redoc_html(
        openapi_url="/openapi.json", title="SmartMealPlanner API Redoc"
    )


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, world"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
