from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring and load balancer health checks."""
    return {"status": "healthy", "message": "PantryPilot API is running"}
