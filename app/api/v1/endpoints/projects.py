import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireRole, TenantContext, get_db_session
from app.core.exceptions import EntityNotFoundException
from app.models.enums import OrgRole
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project (Requires Manager)",
)
async def create_project(
    payload: ProjectCreate,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.MANAGER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Project:
    service = ProjectService(session, ctx.organization_id)
    return await service.create_project(payload)


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List all projects in the organization",
)
async def list_projects(
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[Project]:
    repo = ProjectRepository(session, ctx.organization_id)
    projects = await repo.list_paginated(offset=0, limit=100)
    return list(projects)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details by ID",
)
async def get_project(
    project_id: uuid.UUID,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Project:
    repo = ProjectRepository(session, ctx.organization_id)
    project = await repo.get_by_id(project_id)
    if not project:
        raise EntityNotFoundException("Project", project_id)
    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project details or archive (Requires Manager)",
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.MANAGER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Project:
    service = ProjectService(session, ctx.organization_id)
    return await service.update_project(project_id, payload)
