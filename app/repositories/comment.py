import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.task import Comment
from app.repositories.base import TenantScopedRepository


class CommentRepository(TenantScopedRepository[Comment]):
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        super().__init__(Comment, session, organization_id)

    async def list_comments_cursor(
        self,
        task_id: uuid.UUID,
        cursor_data: tuple[datetime, uuid.UUID] | None,
        limit: int,
    ) -> tuple[Sequence[Comment], bool]:
        criteria = [
            Comment.organization_id == self.organization_id,
            Comment.task_id == task_id,
        ]
        if cursor_data:
            cursor_ts, cursor_id = cursor_data
            criteria.append(
                or_(
                    Comment.created_at > cursor_ts,
                    (Comment.created_at == cursor_ts) & (Comment.id > cursor_id),
                )
            )

        stmt = (
            select(Comment)
            .where(*criteria)
            .options(joinedload(Comment.author))
            .order_by(Comment.created_at.asc(), Comment.id.asc())
            .limit(limit + 1)
        )
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())

        has_more = len(records) > limit
        items = records[:limit]
        return items, has_more
