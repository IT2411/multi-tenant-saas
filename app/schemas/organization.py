import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.models.enums import OrgRole
from app.schemas.common import CoreModel


class OrganizationUpdate(CoreModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    logo_url: str | None = None


class OrganizationResponse(CoreModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None
    is_active: bool
    created_at: datetime


class OrgMemberInviteRequest(CoreModel):
    email: EmailStr
    role: OrgRole = OrgRole.MEMBER


class OrgMemberUpdateRoleRequest(CoreModel):
    role: OrgRole


class OrgMemberDetailResponse(CoreModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    avatar_url: str | None
    role: OrgRole
    joined_at: datetime
