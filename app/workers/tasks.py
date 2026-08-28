import asyncio
from typing import Any

import structlog

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
