from fastapi import APIRouter
from backend.core.config import settings

router = APIRouter()


@router.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Simple health check endpoint returning system status."""
    return {
        "status": "healthy",
        "service": "CLARIO Backend",
        "tagline": "Come confused. Leave with clarity.",
        "environment": settings.ENVIRONMENT,
    }
