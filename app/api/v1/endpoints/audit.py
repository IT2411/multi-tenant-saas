import math
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireRole, TenantContext, get_db_session
from app.models.enums import AuditAction, OrgRole
from app.repositories.audit import AuditLogRepository
from app.schemas.audit import AuditLogFilterParams, AuditLogResponse
from app.schemas.pagination import OffsetPageResponse

router = APIRouter(prefix="/audit-logs", tags=["Audit Trail"])


@router.get(
    "",
    response_model=OffsetPageResponse[AuditLogResponse],
    summary="Query audit trail logs with deep filtering (Requires Admin)",
)
async def query_audit_logs(
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    action: AuditAction | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> OffsetPageResponse[AuditLogResponse]:
    repo = AuditLogRepository(session, ctx.organization_id)
    filters = AuditLogFilterParams(
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
    )
    offset = (page - 1) * page_size
    items, total = await repo.list_audit_logs(filters, offset, page_size)
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    response_items = [
        AuditLogResponse(
            id=log.id,
            organization_id=log.organization_id,
            actor_id=log.actor_id,
            actor_name=log.actor.full_name if log.actor else None,
            actor_email=log.actor.email if log.actor else None,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            action=log.action,
            before_state=log.before_state,
            after_state=log.after_state,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            timestamp=log.timestamp,
        )
        for log in items
    ]

    return OffsetPageResponse(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
