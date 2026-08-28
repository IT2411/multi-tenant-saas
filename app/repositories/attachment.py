import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Attachment
from app.repositories.base import TenantScopedRepository


class AttachmentRepository(TenantScopedRepository[Attachment]):
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        super().__init__(Attachment, session, organization_id)

    async def list_by_task(self, task_id: uuid.UUID) -> Sequence[Attachment]:
        stmt = (
            select(Attachment)
            .where(
                Attachment.organization_id == self.organization_id,
                Attachment.task_id == task_id,
            )
            .order_by(Attachment.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
