import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.models.enums import OrgRole
from app.schemas.common import CoreModel


class UserRegisterRequest(CoreModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    organization_name: str | None = Field(default=None, min_length=2, max_length=100)


class UserLoginRequest(CoreModel):
    email: EmailStr
    password: str


class TokenResponse(CoreModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds


class TokenRefreshRequest(CoreModel):
    refresh_token: str


class OrgMembershipOut(CoreModel):
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    role: OrgRole


class UserResponse(CoreModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime
    memberships: list[OrgMembershipOut] = Field(default_factory=list)
