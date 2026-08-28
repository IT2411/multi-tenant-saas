import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.exceptions import AppException
from app.schemas.common import ErrorDetail, ProblemDetailResponse

logger = structlog.get_logger(__name__)


class RequestContextLogMiddleware(BaseHTTPMiddleware):
    """Assigns X-Request-ID and tracks request lifecycle duration in milliseconds."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-MS"] = f"{process_time:.2f}"

            logger.info(
                "http_request_finished",
                status_code=response.status_code,
                duration_ms=round(process_time, 2),
            )
            return response
        except Exception as exc:
            process_time = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "http_request_unhandled_failure",
                duration_ms=round(process_time, 2),
                error=str(exc),
            )
            raise exc


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    request_id = structlog.contextvars.get_contextvars().get("request_id", str(uuid.uuid4()))
    payload = ProblemDetailResponse(
        type=exc.type_uri,
        title=exc.title,
        status=exc.status_code,
        detail=exc.message,
        instance=request.url.path,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(mode="json"),
        headers={"X-Request-ID": request_id},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = structlog.contextvars.get_contextvars().get("request_id", str(uuid.uuid4()))
    payload = ProblemDetailResponse(
        type="about:blank",
        title="HTTP Error",
        status=exc.status_code,
        detail=str(exc.detail),
        instance=request.url.path,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(mode="json"),
        headers={"X-Request-ID": request_id},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = structlog.contextvars.get_contextvars().get("request_id", str(uuid.uuid4()))
    errors: list[ErrorDetail] = []
    for err in exc.errors():
        loc = " -> ".join([str(p) for p in err.get("loc", [])])
        errors.append(ErrorDetail(field=loc, issue=err.get("msg", "Invalid value")))

    payload = ProblemDetailResponse(
        type="https://api.saas.platform/errors/validation-failed",
        title="Schema Validation Error",
        status=422,
        detail="The supplied request payload failed schema validation constraints.",
        instance=request.url.path,
        request_id=request_id,
        invalid_params=errors,
    )
    return JSONResponse(
        status_code=422,
        content=payload.model_dump(mode="json"),
        headers={"X-Request-ID": request_id},
    )


async def global_unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = structlog.contextvars.get_contextvars().get("request_id", str(uuid.uuid4()))
    logger.critical("fatal_unhandled_system_exception", exc_info=exc)
    payload = ProblemDetailResponse(
        type="https://api.saas.platform/errors/internal-error",
        title="Internal Infrastructure Failure",
        status=500,
        detail="An internal server error occurred while processing the request.",
        instance=request.url.path,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=500,
        content=payload.model_dump(mode="json"),
        headers={"X-Request-ID": request_id},
    )
