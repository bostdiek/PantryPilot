from fastapi import APIRouter

from schemas.api import ApiResponse


router = APIRouter()


@router.get("/health", response_model=ApiResponse[dict[str, str]])
def health_check() -> ApiResponse[dict[str, str]]:
    """Health check endpoint for monitoring and load balancer health checks."""
    return ApiResponse(
        success=True,
        data={"status": "healthy", "message": "PantryPilot API is running"},
        message="Health check successful",
    )
