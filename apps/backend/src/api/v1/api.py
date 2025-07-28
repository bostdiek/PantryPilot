from fastapi import APIRouter

from .health import router as health_router


api_router = APIRouter()

# Include all v1 routers
api_router.include_router(health_router, tags=["health"])
