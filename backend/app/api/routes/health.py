from fastapi import APIRouter
from datetime import datetime, timezone

from app.schemas.health import HealthResponse
from app.config import settings
from app.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Health check endpoint. Returns service status and metadata."""
    logger.info("Health check requested")

    # Placeholder DB check — will be replaced once SQLAlchemy engine is wired up
    db_status = "not_configured"
    try:
        if settings.DATABASE_URL:
            db_status = "configured"
    except Exception as exc:
        logger.warning("DB check failed: %s", exc)
        db_status = "error"

    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
        environment=settings.ENV,
        db_status=db_status,
        message="Ontology Graph Studio backend is running",
    )
