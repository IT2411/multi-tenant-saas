import uuid
from dataclasses import dataclass
from typing import Annotated, ClassVar

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import decode_jwt_token
from app.models.enums import OrgRole
from app.models.user import User
from app.repositories.organization import OrganizationMemberRepository
from app.repositories.user import UserRepository

__all__ = [
    "RequireRole",
    "TenantContext",
    "get_current_user",
    "get_db_session",
    "security_bearer",
]

security_bearer = HTTPBearer(auto_error=True)


@dataclass
class TenantContext:
    """Encapsulates the active authenticated user, tenant ID, and their verified role."""

    user: User
    organization_id: uuid.UUID
    role: OrgRole


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_bearer)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Validates JWT access token signature, expiration, and user account status."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_jwt_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise credentials_exception from None

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found",
        )
    return user


class RequireRole:
    """Dependency that ensures the user belongs to the target organization

    with at least the minimum role hierarchy requirement.
    """

    ROLE_HIERARCHY: ClassVar[dict[OrgRole, int]] = {
        OrgRole.VIEWER: 1,
        OrgRole.MEMBER: 2,
        OrgRole.MANAGER: 3,
        OrgRole.ADMIN: 4,
        OrgRole.OWNER: 5,
    }

    def __init__(self, min_role: OrgRole) -> None:
        self.min_role = min_role

    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
        x_organization_id: Annotated[uuid.UUID, Header(alias="X-Organization-ID")],
    ) -> TenantContext:
        member_repo = OrganizationMemberRepository(session)
        membership = await member_repo.get_membership(x_organization_id, current_user.id)

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of the requested organization.",
            )

        user_level = self.ROLE_HIERARCHY.get(membership.role, 0)
        required_level = self.ROLE_HIERARCHY.get(self.min_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Requires '{self.min_role.value}' role or higher.",
            )

        return TenantContext(
            user=current_user,
            organization_id=x_organization_id,
            role=membership.role,
        )
