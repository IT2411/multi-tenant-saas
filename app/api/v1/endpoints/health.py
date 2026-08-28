import structlog
from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.core.database import session_manager
from app.core.redis import redis_client
from app.schemas.common import HealthResponse, ReadinessResponse
from app.services.storage import S3StorageService

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get(
    "/healthz",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
)
async def liveness_check() -> HealthResponse:
    """Non-blocking liveness probe asserting process loop responsiveness."""
    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/readyz",
    response_model=ReadinessResponse,
    summary="Deep Infrastructure Readiness Probe",
)
async def readiness_check(response: Response) -> ReadinessResponse:
    """Verifies active connectivity to PostgreSQL, Redis, and Object Storage."""
    db_healthy = False
    redis_healthy = False
    storage_healthy = False

    # 1. Check Database
    try:
        db_healthy = await session_manager.health_check()
    except Exception as exc:
        logger.error("readiness_check_db_failure", error=str(exc))

    # 2. Check Redis
    try:
        pong = await redis_client.ping()
        redis_healthy = bool(pong is True or pong == "PONG")
    except Exception as exc:
        logger.error("readiness_check_redis_failure", error=str(exc))

    # 3. Check Object Storage (S3 / MinIO)
    try:
        storage = S3StorageService()
        await storage.ensure_bucket_exists()
        storage_healthy = True
    except Exception as exc:
        logger.error("readiness_check_storage_failure", error=str(exc))

    is_all_ready = db_healthy and redis_healthy and storage_healthy
    if not is_all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if is_all_ready else "unready",
        database=db_healthy,
        redis=redis_healthy,
        storage=storage_healthy,
    )
