import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireRole, TenantContext, get_db_session
from app.core.exceptions import EntityConflictException, EntityNotFoundException
from app.core.pagination import decode_cursor, encode_cursor
from app.models.enums import OrgRole, TaskPriority, TaskStatus
from app.models.task import Task
from app.repositories.task import TaskRepository
from app.schemas.pagination import CursorPageResponse, OffsetPageResponse
from app.schemas.task import TaskCreate, TaskFilterParams, TaskResponse, TaskUpdate
from app.services.task import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task (Requires Member)",
)
async def create_task(
    payload: TaskCreate,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.MEMBER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Task:
    service = TaskService(session, ctx.organization_id)
    return await service.create_task(
        project_id=payload.project_id,
        reporter_id=ctx.user.id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
    )


@router.get(
    "",
    response_model=OffsetPageResponse[TaskResponse],
    summary="List tasks with offset pagination, filtering, search, and sorting",
)
async def list_tasks_offset(
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    project_id: uuid.UUID | None = None,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    assignee_id: uuid.UUID | None = None,
    search: str | None = None,
    sort_by: str = "created_at:desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> OffsetPageResponse[TaskResponse]:
    repo = TaskRepository(session, ctx.organization_id)
    filters = TaskFilterParams(
        project_id=project_id,
        status=task_status,
        priority=priority,
        assignee_id=assignee_id,
        search=search,
        sort_by=sort_by,
    )
    offset = (page - 1) * page_size
    items, total = await repo.list_tasks_offset(filters, offset, page_size)
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return OffsetPageResponse(
        items=[TaskResponse.model_validate(t, from_attributes=True) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/feed",
    response_model=CursorPageResponse[TaskResponse],
    summary="List tasks with high-performance cursor pagination",
)
async def list_tasks_feed(
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    project_id: uuid.UUID | None = None,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CursorPageResponse[TaskResponse]:
    repo = TaskRepository(session, ctx.organization_id)
    filters = TaskFilterParams(project_id=project_id, status=task_status)
    cursor_data = decode_cursor(cursor) if cursor else None

    items, has_more = await repo.list_tasks_cursor(filters, cursor_data, limit)
    next_cursor = None
    if has_more and items:
        last_item = items[-1]
        next_cursor = encode_cursor(last_item.created_at, last_item.id)

    return CursorPageResponse(
        items=[TaskResponse.model_validate(t, from_attributes=True) for t in items],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task by ID",
)
async def get_task(
    task_id: uuid.UUID,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Task:
    repo = TaskRepository(session, ctx.organization_id)
    task = await repo.get_by_id(task_id)
    if not task:
        raise EntityNotFoundException("Task", task_id)
    return task


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update task with OCC concurrency protection (Requires Member)",
)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.MEMBER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Task:
    service = TaskService(session, ctx.organization_id)
    if payload.status:
        return await service.update_task_status_occ(
            task_id=task_id,
            actor_id=ctx.user.id,
            new_status=payload.status,
            expected_version=payload.expected_version,
        )

    repo = TaskRepository(session, ctx.organization_id)
    task = await repo.get_by_id(task_id)
    if not task:
        raise EntityNotFoundException("Task", task_id)
    if task.version_id != payload.expected_version:
        raise EntityConflictException("Task was modified by another concurrent transaction.")

    if payload.title is not None:
        task.title = payload.title.strip()
    if payload.description is not None:
        task.description = payload.description
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.assignee_id is not None:
        task.assignee_id = payload.assignee_id
    if payload.due_date is not None:
        task.due_date = payload.due_date

    task.version_id += 1
    await session.commit()
    await session.refresh(task)
    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a task (Requires Member)",
)
async def delete_task(
    task_id: uuid.UUID,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.MEMBER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    repo = TaskRepository(session, ctx.organization_id)
    success = await repo.soft_delete(task_id)
    if not success:
        raise EntityNotFoundException("Task", task_id)
    await session.commit()
