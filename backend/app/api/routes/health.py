from fastapi import APIRouter, Depends, HTTPException, status
from app.db.connection import get_db
from app.config.settings import settings

router = APIRouter()

@router.get("/health")
async def health_liveness():
    """Liveness probe indicating the application process is running."""
    return {
        "status": "online",
        "environment": settings.ENVIRONMENT,
        "service": "Recovr.ai Backend"
    }

@router.get("/readiness")
async def health_readiness(db = Depends(get_db)):
    """Readiness probe checking backend database and dependency connectivity."""
    try:
        await db.client.admin.command('ping')
        return {
            "status": "ready",
            "environment": settings.ENVIRONMENT,
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unavailable: Database connection failed."
        )
