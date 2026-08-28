from collections.abc import Sequence
from typing import Any, Callable, ClassVar
from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.tasks import (
    cleanup_soft_deleted_tasks_job,
    send_invitation_email,
    send_task_notification,
)


class WorkerSettings:
    """ARQ Worker configuration with scheduled maintenance cron jobs."""

    functions: ClassVar[Sequence[Callable[..., Any]]] = [
        send_invitation_email,
        send_task_notification,
        cleanup_soft_deleted_tasks_job,
    ]
    cron_jobs: ClassVar[list[Any]] = [
        cron(
            "app.workers.tasks.cleanup_soft_deleted_tasks_job",
            hour=3,
            minute=0,
        ),  # Runs daily at 03:00 UTC
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
    retry_delay: int | float = 5