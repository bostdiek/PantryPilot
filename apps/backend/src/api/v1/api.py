from fastapi import APIRouter, Depends

from dependencies.auth import get_current_user

from .auth import router as auth_router
from .health import router as health_router
from .mealplans import meals_router, router as mealplans_router
from .recipes import router as recipes_router


# Public API router (health, auth)
api_router = APIRouter()

# Include public routers
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)


# Protected routers: include with a router-level dependency so all routes
# require authentication by default. Use get_current_user dependency to
# surface the OAuth2 security scheme in OpenAPI as well.
protected_deps = [Depends(get_current_user)]
api_router.include_router(recipes_router, dependencies=protected_deps)
api_router.include_router(mealplans_router, dependencies=protected_deps)
api_router.include_router(meals_router, dependencies=protected_deps)
