from collections.abc import Callable, Sequence
from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.tasks import send_invitation_email, send_task_notification


class WorkerSettings:
    """ARQ Worker configuration."""

    functions: ClassVar[Sequence[Callable[..., Any]]] = [
        send_invitation_email,
        send_task_notification,
    ]
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
    )
    max_jobs: int = 20
    job_timeout: int = 60
    max_tries: int = 3
    retry_delay: int | float = 5  # Initial backoff in seconds
