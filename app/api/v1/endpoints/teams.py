import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireRole, TenantContext, get_db_session
from app.models.enums import OrgRole
from app.repositories.team import TeamRepository
from app.schemas.team import TeamCreate, TeamMemberAddRequest, TeamResponse
from app.services.team import TeamService

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.post(
    "",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new team (Requires Manager)",
)
async def create_team(
    payload: TeamCreate,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.MANAGER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TeamResponse:
    service = TeamService(session, ctx.organization_id)
    team = await service.create_team(payload)
    return await service.get_team_detail(team.id)


@router.get(
    "",
    response_model=list[TeamResponse],
    summary="List all teams in organization",
)
async def list_teams(
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[TeamResponse]:
    repo = TeamRepository(session, ctx.organization_id)
    service = TeamService(session, ctx.organization_id)
    teams = await repo.list_paginated(offset=0, limit=100)
    return [await service.get_team_detail(t.id) for t in teams]


@router.get(
    "/{team_id}",
    response_model=TeamResponse,
    summary="Get team details and members",
)
async def get_team(
    team_id: uuid.UUID,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TeamResponse:
    service = TeamService(session, ctx.organization_id)
    return await service.get_team_detail(team_id)


@router.post(
    "/{team_id}/members",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Add user to team (Requires Manager)",
)
async def add_team_member(
    team_id: uuid.UUID,
    payload: TeamMemberAddRequest,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.MANAGER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    service = TeamService(session, ctx.organization_id)
    await service.add_member(team_id, payload.user_id)
