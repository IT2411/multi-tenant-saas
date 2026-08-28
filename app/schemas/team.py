import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import CoreModel


class TeamCreate(CoreModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=100)
    description: str | None = None


class TeamUpdate(CoreModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None


class TeamMemberResponse(CoreModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    joined_at: datetime


class TeamResponse(CoreModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    created_at: datetime
    members: list[TeamMemberResponse] = Field(default_factory=list)


class TeamMemberAddRequest(CoreModel):
    user_id: uuid.UUID
