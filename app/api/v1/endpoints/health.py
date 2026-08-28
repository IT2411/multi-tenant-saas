import structlog
from fastapi import APIRouter, status

from app.core.config import settings
from app.core.database import session_manager
from app.schemas.common import HealthResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get(
    "/healthz",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness and Readiness Probe",
)
async def health_check() -> HealthResponse:
    """Verifies internal database infrastructure readiness."""
    db_connected = False
    try:
        db_connected = await session_manager.health_check()
    except Exception as e:
        logger.error("health_check_database_unreachable", error=str(e))

    return HealthResponse(
        status="healthy" if db_connected else "unhealthy",
        environment=settings.ENVIRONMENT,
        database_connected=db_connected,
    )
