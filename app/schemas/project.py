import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import CoreModel


class ProjectCreate(CoreModel):
    name: str = Field(min_length=2, max_length=100)
    key: str = Field(min_length=2, max_length=10)
    description: str | None = None
    team_id: uuid.UUID | None = None


class ProjectUpdate(CoreModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None
    team_id: uuid.UUID | None = None
    is_archived: bool | None = None
    expected_version: int = Field(ge=1)  # OCC Guard


class ProjectResponse(CoreModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    team_id: uuid.UUID | None
    name: str
    key: str
    description: str | None
    is_archived: bool
    version_id: int
    created_at: datetime
