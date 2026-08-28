import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import TaskPriority, TaskStatus
from app.schemas.common import CoreModel


class TaskCreate(CoreModel):
    project_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    due_date: datetime | None = None


class TaskUpdate(CoreModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: uuid.UUID | None = None
    due_date: datetime | None = None
    expected_version: int = Field(ge=1)  # Required for OCC concurrency guard


class TaskResponse(CoreModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    parent_id: uuid.UUID | None
    reporter_id: uuid.UUID
    assignee_id: uuid.UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    version_id: int
    created_at: datetime
    updated_at: datetime


class TaskFilterParams(CoreModel):
    project_id: uuid.UUID | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: uuid.UUID | None = None
    reporter_id: uuid.UUID | None = None
    search: str | None = None
    sort_by: str = "created_at:desc"  # field:direction (e.g. "created_at:desc", "priority:asc")
