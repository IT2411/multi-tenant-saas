from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import RequireRole, TenantContext, get_db_session
from app.core.exceptions import EntityConflictException, EntityNotFoundException
from app.models.enums import OrgRole
from app.models.organization import Organization, OrganizationMember
from app.repositories.organization import (
    OrganizationMemberRepository,
    OrganizationRepository,
)
from app.repositories.user import UserRepository
from app.schemas.organization import (
    OrganizationResponse,
    OrganizationUpdate,
    OrgMemberDetailResponse,
    OrgMemberInviteRequest,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get(
    "/current",
    response_model=OrganizationResponse,
    summary="Get current active organization details",
)
async def get_current_organization(
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Organization:
    org_repo = OrganizationRepository(session)
    org = await org_repo.get_by_id(ctx.organization_id)
    if not org:
        raise EntityNotFoundException("Organization", ctx.organization_id)
    return org


@router.patch(
    "/current",
    response_model=OrganizationResponse,
    summary="Update current organization (Requires Admin)",
)
async def update_current_organization(
    payload: OrganizationUpdate,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Organization:
    org_repo = OrganizationRepository(session)
    org = await org_repo.get_by_id(ctx.organization_id)
    if not org:
        raise EntityNotFoundException("Organization", ctx.organization_id)

    if payload.name is not None:
        org.name = payload.name.strip()
    if payload.logo_url is not None:
        org.logo_url = payload.logo_url

    await session.commit()
    await session.refresh(org)
    return org


@router.get(
    "/current/members",
    response_model=list[OrgMemberDetailResponse],
    summary="List all members in the organization",
)
async def list_organization_members(
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[OrgMemberDetailResponse]:
    stmt = (
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == ctx.organization_id)
        .options(joinedload(OrganizationMember.user))
        .order_by(OrganizationMember.created_at.asc())
    )
    result = await session.execute(stmt)
    members = result.scalars().all()

    return [
        OrgMemberDetailResponse(
            id=m.id,
            user_id=m.user_id,
            email=m.user.email,
            full_name=m.user.full_name,
            avatar_url=m.user.avatar_url,
            role=m.role,
            joined_at=m.created_at,
        )
        for m in members
    ]


@router.post(
    "/current/members/invite",
    response_model=OrgMemberDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite existing user to organization (Requires Admin)",
)
async def invite_member(
    payload: OrgMemberInviteRequest,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrgMemberDetailResponse:
    user_repo = UserRepository(session)
    member_repo = OrganizationMemberRepository(session)

    user = await user_repo.get_by_email(payload.email)
    if not user:
        raise EntityNotFoundException("User", payload.email)

    existing = await member_repo.get_membership(ctx.organization_id, user.id)
    if existing:
        raise EntityConflictException("User is already a member of this organization.")

    new_member = await member_repo.create(
        organization_id=ctx.organization_id,
        user_id=user.id,
        role=payload.role,
    )
    await session.commit()

    return OrgMemberDetailResponse(
        id=new_member.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=new_member.role,
        joined_at=new_member.created_at,
    )
