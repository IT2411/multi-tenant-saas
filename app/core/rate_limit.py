import time
from collections.abc import Callable
from typing import Any

import structlog
from fastapi import HTTPException, Request, Response, status

from app.core.redis import redis_client

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Sliding-window rate limiter using Redis sorted sets."""

    def __init__(
        self,
        requests_per_window: int,
        window_seconds: int,
        key_generator: Callable[[Request], str] | None = None,
    ) -> None:
        self.limit = requests_per_window
        self.window = window_seconds
        self.key_generator = key_generator

    async def __call__(self, request: Request, response: Response) -> None:
        current_ts = time.time()
        window_start = current_ts - self.window

        if self.key_generator:
            identifier = self.key_generator(request)
        else:
            client_ip = request.client.host if request.client else "unknown"
            path = request.url.path
            identifier = f"rate_limit:{client_ip}:{path}"

        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(identifier, 0, window_start)
        pipe.zadd(identifier, {f"{current_ts}:{time.perf_counter()}": current_ts})
        pipe.zcard(identifier)
        pipe.expire(identifier, self.window)

        results: list[Any] = await pipe.execute()
        request_count: int = results[2]

        remaining = max(0, self.limit - request_count)
        reset_time = int(current_ts + self.window)

        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        if request_count > self.limit:
            retry_after = str(self.window)
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                requests=request_count,
                limit=self.limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.limit} requests per {self.window} seconds allowed.",
                headers={
                    "Retry-After": retry_after,
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )
