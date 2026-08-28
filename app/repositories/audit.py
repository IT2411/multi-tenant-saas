import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.audit import AuditLog
from app.repositories.base import TenantScopedRepository
from app.schemas.audit import AuditLogFilterParams


class AuditLogRepository(TenantScopedRepository[AuditLog]):
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        super().__init__(AuditLog, session, organization_id)

    def _build_criteria(self, filters: AuditLogFilterParams) -> list[ColumnElement[bool]]:
        criteria: list[ColumnElement[bool]] = [
            AuditLog.organization_id == self.organization_id,
        ]
        if filters.entity_type:
            criteria.append(AuditLog.entity_type == filters.entity_type)
        if filters.entity_id:
            criteria.append(AuditLog.entity_id == filters.entity_id)
        if filters.actor_id:
            criteria.append(AuditLog.actor_id == filters.actor_id)
        if filters.action:
            criteria.append(AuditLog.action == filters.action)
        if filters.start_date:
            criteria.append(AuditLog.timestamp >= filters.start_date)
        if filters.end_date:
            criteria.append(AuditLog.timestamp <= filters.end_date)
        return criteria

    async def list_audit_logs(
        self,
        filters: AuditLogFilterParams,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[AuditLog], int]:
        criteria = self._build_criteria(filters)

        count_stmt = select(func.count()).select_from(AuditLog).where(*criteria)
        total_result = await self.session.execute(count_stmt)
        total = int(total_result.scalar_one() or 0)

        stmt = (
            select(AuditLog)
            .where(*criteria)
            .options(joinedload(AuditLog.actor))
            .order_by(AuditLog.timestamp.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total
