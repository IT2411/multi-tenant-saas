import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireRole, TenantContext, get_db_session
from app.core.cache import CacheService
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
    summary="Get project details by ID (Cached)",
)
async def get_project(
    project_id: uuid.UUID,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectResponse:
    cache_key = CacheService.build_key(
        "tenant", str(ctx.organization_id), "projects", str(project_id)
    )
    cached_project = await CacheService.get(cache_key, ProjectResponse)
    if cached_project:
        return cached_project

    repo = ProjectRepository(session, ctx.organization_id)
    project = await repo.get_by_id(project_id)
    if not project:
        raise EntityNotFoundException("Project", project_id)

    response = ProjectResponse.model_validate(project, from_attributes=True)
    await CacheService.set(cache_key, response, ttl_seconds=300)
    return response


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project details (Invalidates Cache)",
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.MANAGER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectResponse:
    service = ProjectService(session, ctx.organization_id)
    project = await service.update_project(project_id, payload)

    # Invalidate Cache
    cache_key = CacheService.build_key(
        "tenant", str(ctx.organization_id), "projects", str(project_id)
    )
    await CacheService.delete(cache_key)

    return ProjectResponse.model_validate(project, from_attributes=True)
