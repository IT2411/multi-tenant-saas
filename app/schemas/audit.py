import uuid
from datetime import datetime
from typing import Any

from app.models.enums import AuditAction
from app.schemas.common import CoreModel


class AuditLogResponse(CoreModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_name: str | None = None
    actor_email: str | None = None
    entity_type: str
    entity_id: uuid.UUID
    action: AuditAction
    before_state: dict[str, Any] | None
    after_state: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    timestamp: datetime


class AuditLogFilterParams(CoreModel):
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    action: AuditAction | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
