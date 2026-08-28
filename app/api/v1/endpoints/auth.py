from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.core.rate_limit import RateLimiter
from app.models.user import User
from app.schemas.auth import (
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Rate limiters: 5 login attempts / min, 3 registrations / min
login_rate_limiter = RateLimiter(requests_per_window=5, window_seconds=60)
register_rate_limiter = RateLimiter(requests_per_window=3, window_seconds=60)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_rate_limiter)],
    summary="Register a new user and workspace",
)
async def register(
    payload: UserRegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    auth_service = AuthService(session)
    _, tokens = await auth_service.register(payload)
    return tokens


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(login_rate_limiter)],
    summary="Log in and retrieve token pair",
)
async def login(
    payload: UserLoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    auth_service = AuthService(session)
    _, tokens = await auth_service.authenticate(payload.email, payload.password)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and retrieve new access token",
)
async def refresh(
    payload: TokenRefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    auth_service = AuthService(session)
    return await auth_service.refresh_tokens(payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke refresh token",
)
async def logout(
    payload: TokenRefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    auth_service = AuthService(session)
    await auth_service.logout(payload.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile and memberships",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    auth_service = AuthService(session)
    return await auth_service.get_user_profile(current_user.id)
