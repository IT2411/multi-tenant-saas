from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import session_manager
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.core.middleware import (
    RequestContextLogMiddleware,
    app_exception_handler,
    global_unhandled_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.telemetry import setup_telemetry
from app.services.storage import S3StorageService

setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manages application startup warm-ups and graceful shutdown drains."""
    logger.info(
        "server_startup_sequence_initiated",
        project_name=settings.PROJECT_NAME,
        env=settings.ENVIRONMENT,
    )
    # 1. Warm up database connection pool
    try:
        is_healthy = await session_manager.health_check()
        logger.info("database_connectivity_verified", pool_status=is_healthy)
    except Exception as exc:
        logger.critical("database_initialization_failed", exc_info=exc)
        raise exc

    # 2. Verify / Provision Object Storage Bucket
    try:
        storage = S3StorageService()
        await storage.ensure_bucket_exists()
        logger.info("storage_bucket_verified", bucket=settings.S3_BUCKET_NAME)
    except Exception as exc:
        logger.warning("storage_bucket_init_warning", error=str(exc))

    yield

    logger.info("server_shutdown_sequence_initiated")
    await session_manager.close()
    logger.info("server_shutdown_sequence_completed")


def create_application() -> FastAPI:
    """Builds and initializes the FastAPI application."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
        if settings.ENVIRONMENT != "production"
        else None,
        docs_url=f"{settings.API_V1_STR}/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url=f"{settings.API_V1_STR}/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # Telemetry
    telemetry = setup_telemetry(application)
    telemetry.expose(application, endpoint="/metrics")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.ALLOWED_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestContextLogMiddleware)

    application.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    application.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,  # type: ignore[arg-type]
    )
    application.add_exception_handler(Exception, global_unhandled_exception_handler)

    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app: FastAPI = create_application()
