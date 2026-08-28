import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.repositories.base import TenantScopedRepository
from app.schemas.task import TaskFilterParams


class TaskRepository(TenantScopedRepository[Task]):
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        super().__init__(Task, session, organization_id)

    def _build_filter_criteria(self, filters: TaskFilterParams) -> list[ColumnElement[bool]]:
        criteria: list[ColumnElement[bool]] = [
            Task.organization_id == self.organization_id,
            Task.is_deleted.is_(False),
        ]
        if filters.project_id:
            criteria.append(Task.project_id == filters.project_id)
        if filters.status:
            criteria.append(Task.status == filters.status)
        if filters.priority:
            criteria.append(Task.priority == filters.priority)
        if filters.assignee_id:
            criteria.append(Task.assignee_id == filters.assignee_id)
        if filters.reporter_id:
            criteria.append(Task.reporter_id == filters.reporter_id)
        if filters.search:
            search_pattern = f"%{filters.search.strip()}%"
            criteria.append(
                or_(
                    Task.title.ilike(search_pattern),
                    Task.description.ilike(search_pattern),
                )
            )
        return criteria

    async def list_tasks_offset(
        self,
        filters: TaskFilterParams,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Task], int]:
        criteria = self._build_filter_criteria(filters)

        # Count total
        count_stmt = select(func.count()).select_from(Task).where(*criteria)
        total_result = await self.session.execute(count_stmt)
        total = int(total_result.scalar_one() or 0)

        # Query items
        stmt = select(Task).where(*criteria)
        if filters.sort_by == "created_at:asc":
            stmt = stmt.order_by(Task.created_at.asc(), Task.id.asc())
        else:
            stmt = stmt.order_by(Task.created_at.desc(), Task.id.desc())

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def list_tasks_cursor(
        self,
        filters: TaskFilterParams,
        cursor_data: tuple[datetime, uuid.UUID] | None,
        limit: int,
    ) -> tuple[Sequence[Task], bool]:
        criteria = self._build_filter_criteria(filters)

        # Keyset pagination condition: (created_at < cursor_ts) OR (created_at == cursor_ts AND id < cursor_id)
        if cursor_data:
            cursor_ts, cursor_id = cursor_data
            criteria.append(
                or_(
                    Task.created_at < cursor_ts,
                    (Task.created_at == cursor_ts) & (Task.id < cursor_id),
                )
            )

        # Fetch limit + 1 to check for next page presence
        stmt = (
            select(Task)
            .where(*criteria)
            .order_by(Task.created_at.desc(), Task.id.desc())
            .limit(limit + 1)
        )
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())

        has_more = len(records) > limit
        items = records[:limit]
        return items, has_more
