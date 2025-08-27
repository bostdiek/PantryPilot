from fastapi import APIRouter

from .health import router as health_router
from .recipes import router as recipes_router


api_router = APIRouter()

# Include all v1 routers
api_router.include_router(health_router, tags=["health"])
api_router.include_router(recipes_router)
