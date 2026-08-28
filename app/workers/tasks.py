import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import delete

from app.core.database import session_manager
from app.models.task import Task

logger = structlog.get_logger(__name__)


async def send_invitation_email(
    _ctx: dict[str, Any],
    recipient_email: str,
    org_name: str,
    inviter_name: str,
) -> bool:
    """Async background task to deliver workspace invitations."""
    logger.info(
        "sending_invitation_email_initiated",
        recipient=recipient_email,
        org=org_name,
        inviter=inviter_name,
    )
    await asyncio.sleep(0.05)
    logger.info("invitation_email_delivered", recipient=recipient_email)
    return True


async def send_task_notification(
    _ctx: dict[str, Any],
    user_id: str,
    task_title: str,
    event_type: str,
) -> bool:
    """Async background task to push notifications to assignees."""
    logger.info(
        "task_notification_enqueued",
        user_id=user_id,
        task_title=task_title,
        event_type=event_type,
    )
    await asyncio.sleep(0.05)
    return True


async def cleanup_soft_deleted_tasks_job(_ctx: dict[str, Any], days_threshold: int = 30) -> int:
    """Purges soft-deleted tasks older than the retention threshold."""
    cutoff_time = datetime.now(UTC) - timedelta(days=days_threshold)
    logger.info("cleanup_soft_deleted_tasks_started", cutoff=cutoff_time.isoformat())

    async with session_manager.sessionmaker() as session:
        stmt = (
            delete(Task)
            .where(
                Task.is_deleted.is_(True),
                Task.deleted_at <= cutoff_time,
            )
            .returning(Task.id)
        )
        result = await session.execute(stmt)
        deleted_ids = result.scalars().all()
        await session.commit()

        count = len(deleted_ids)
        logger.info("cleanup_soft_deleted_tasks_completed", purged_count=count)
        return count
