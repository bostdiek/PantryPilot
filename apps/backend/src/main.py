import os
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.api import api_router


def validate_cors_origins(origins_str: str) -> list[str]:
    """Validate and sanitize CORS origins."""
    origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()]
    validated_origins = []

    # Basic URL pattern validation
    url_pattern = re.compile(
        r"^https?://[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*"
        r"(:[0-9]{1,5})?$"
    )

    for origin in origins:
        if url_pattern.match(origin):
            validated_origins.append(origin)
        else:
            print(f"Warning: Invalid CORS origin '{origin}' ignored")

    return validated_origins


app = FastAPI(
    title="PantryPilot API",
    description="A smart pantry management system",
    version="0.1.0",
)

# Configure CORS
origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
origins = validate_cors_origins(origins_str)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, world"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
