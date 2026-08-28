from typing import Any

import structlog
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import settings

logger = structlog.get_logger(__name__)


class JobQueueService:
    _pool: ArqRedis | None = None

    @classmethod
    async def get_pool(cls) -> ArqRedis:
        if cls._pool is None:
            cls._pool = await create_pool(
                RedisSettings(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    database=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                )
            )
        return cls._pool

    @classmethod
    async def enqueue(cls, function_name: str, *args: Any, **kwargs: Any) -> str | None:
        """Enqueues a background job asynchronously without blocking HTTP requests."""
        try:
            pool = await cls.get_pool()
            job = await pool.enqueue_job(function_name, *args, **kwargs)
            return job.job_id if job else None
        except Exception as exc:
            logger.error("job_enqueue_failed", function=function_name, error=str(exc))
            return None
