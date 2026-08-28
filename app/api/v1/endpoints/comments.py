import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireRole, TenantContext, get_db_session
from app.models.enums import OrgRole
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.schemas.pagination import CursorPageResponse
from app.services.comment import CommentService

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["Comments"])


@router.post(
    "",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to a task (Requires Member)",
)
async def create_comment(
    task_id: uuid.UUID,
    payload: CommentCreate,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.MEMBER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CommentResponse:
    service = CommentService(session, ctx.organization_id)
    comment = await service.add_comment(task_id, ctx.user.id, payload)
    return CommentResponse(
        id=comment.id,
        organization_id=comment.organization_id,
        task_id=comment.task_id,
        author_id=ctx.user.id,
        author_name=ctx.user.full_name,
        author_avatar_url=ctx.user.avatar_url,
        content=comment.content,
        is_edited=comment.is_edited,
        created_at=comment.created_at,
    )


@router.get(
    "",
    response_model=CursorPageResponse[CommentResponse],
    summary="List comments with chronological cursor pagination",
)
async def list_comments(
    task_id: uuid.UUID,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> CursorPageResponse[CommentResponse]:
    service = CommentService(session, ctx.organization_id)
    return await service.list_comments(task_id, cursor, limit)


@router.patch(
    "/{comment_id}",
    response_model=CommentResponse,
    summary="Edit comment (Author or Admin)",
)
async def update_comment(
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    payload: CommentUpdate,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.MEMBER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CommentResponse:
    service = CommentService(session, ctx.organization_id)
    comment = await service.update_comment(comment_id, ctx.user.id, ctx.role, payload)
    return CommentResponse(
        id=comment.id,
        organization_id=comment.organization_id,
        task_id=task_id,
        author_id=ctx.user.id,
        author_name=ctx.user.full_name,
        author_avatar_url=ctx.user.avatar_url,
        content=comment.content,
        is_edited=comment.is_edited,
        created_at=comment.created_at,
    )
