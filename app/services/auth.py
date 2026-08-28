import re
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AppException,
    EntityConflictException,
    ForbiddenOperationException,
)
from app.core.redis import TokenBlacklistService
from app.core.security import (
    create_jwt_token,
    decode_jwt_token,
    hash_password,
    verify_password,
)
from app.models.enums import OrgRole
from app.models.user import User
from app.repositories.organization import (
    OrganizationMemberRepository,
    OrganizationRepository,
)
from app.repositories.user import UserRepository
from app.schemas.auth import (
    OrgMembershipOut,
    TokenResponse,
    UserRegisterRequest,
    UserResponse,
)
from app.services.base import BaseService

logger = structlog.get_logger(__name__)

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def slugify(text: str) -> str:
    """Converts a name into a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)


class AuthService(BaseService):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.user_repo = UserRepository(session)
        self.org_repo = OrganizationRepository(session)
        self.member_repo = OrganizationMemberRepository(session)

    async def register(self, payload: UserRegisterRequest) -> tuple[User, TokenResponse]:
        """Atomically registers a new User, provisions their Organization, and binds them as OWNER."""
        async with self.uow.transaction():
            existing_user = await self.user_repo.get_by_email(payload.email)
            if existing_user:
                raise EntityConflictException(f"User with email '{payload.email}' already exists.")

            user = await self.user_repo.create(
                email=payload.email.lower().strip(),
                hashed_password=hash_password(payload.password),
                full_name=payload.full_name.strip(),
                is_active=True,
                is_verified=False,
            )

            org_name = payload.organization_name or f"{user.full_name}'s Workspace"
            base_slug = slugify(org_name)
            unique_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

            org = await self.org_repo.create(
                name=org_name,
                slug=unique_slug,
                is_active=True,
            )

            await self.member_repo.create(
                organization_id=org.id,
                user_id=user.id,
                role=OrgRole.OWNER,
            )

            token_pair = await self._generate_token_pair(user.id)
            return user, token_pair

    async def authenticate(self, email: str, password: str) -> tuple[User, TokenResponse]:
        """Validates credentials and issues an access/refresh token pair."""
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AppException(
                message="Invalid email or password credentials.",
                status_code=401,
                title="Authentication Failed",
                type_uri="https://api.saas.platform/errors/invalid-credentials",
            )

        if not user.is_active:
            raise ForbiddenOperationException("This user account has been deactivated.")

        token_pair = await self._generate_token_pair(user.id)
        return user, token_pair

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Validates refresh token, checks revocation in Redis, and issues a new token pair."""
        try:
            payload = decode_jwt_token(refresh_token)
        except jwt.PyJWTError:
            raise AppException(
                message="Invalid or expired refresh token.",
                status_code=401,
                title="Invalid Token",
            ) from None

        if payload.get("type") != "refresh":
            raise AppException(
                message="Supplied token is not a refresh token.",
                status_code=401,
                title="Invalid Token Type",
            )

        jti = payload["jti"]
        if await TokenBlacklistService.is_token_revoked(jti):
            raise AppException(
                message="Refresh token has been revoked.",
                status_code=401,
                title="Revoked Token",
            )

        user_id = uuid.UUID(payload["sub"])
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise AppException(message="User account is inactive or not found.", status_code=401)

        exp_timestamp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        await TokenBlacklistService.revoke_token(jti, exp_timestamp)

        return await self._generate_token_pair(user.id)

    async def logout(self, refresh_token: str) -> None:
        """Revokes the refresh token in Redis."""
        try:
            payload = decode_jwt_token(refresh_token)
            if payload.get("type") == "refresh":
                exp_timestamp = datetime.fromtimestamp(payload["exp"], tz=UTC)
                await TokenBlacklistService.revoke_token(payload["jti"], exp_timestamp)
        except Exception:
            pass

    async def get_user_profile(self, user_id: uuid.UUID) -> UserResponse:
        """Fetches user entity along with all active organization memberships."""
        user = await self.user_repo.get_user_with_memberships(user_id)
        if not user:
            raise AppException(message="User not found", status_code=404)

        memberships_out = [
            OrgMembershipOut(
                organization_id=m.organization_id,
                organization_name=m.organization.name,
                organization_slug=m.organization.slug,
                role=m.role,
            )
            for m in user.memberships
        ]

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            memberships=memberships_out,
        )

    async def _generate_token_pair(self, user_id: uuid.UUID) -> TokenResponse:
        access_token, _, _ = create_jwt_token(
            subject=user_id,
            token_type="access",
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token, _, _ = create_jwt_token(
            subject=user_id,
            token_type="refresh",
            expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
