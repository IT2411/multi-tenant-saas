import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException, ForbiddenOperationException
from app.core.pagination import decode_cursor, encode_cursor
from app.models.enums import OrgRole
from app.models.task import Comment
from app.repositories.comment import CommentRepository
from app.repositories.task import TaskRepository
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.schemas.pagination import CursorPageResponse
from app.services.base import BaseService


class CommentService(BaseService):
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        super().__init__(session)
        self.organization_id = organization_id
        self.comment_repo = CommentRepository(session, organization_id)
        self.task_repo = TaskRepository(session, organization_id)

    async def add_comment(
        self,
        task_id: uuid.UUID,
        author_id: uuid.UUID,
        payload: CommentCreate,
    ) -> Comment:
        async with self.uow.transaction():
            task = await self.task_repo.get_by_id(task_id)
            if not task:
                raise EntityNotFoundException("Task", task_id)

            return await self.comment_repo.create(
                task_id=task_id,
                author_id=author_id,
                content=payload.content.strip(),
                is_edited=False,
            )

    async def list_comments(
        self,
        task_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> CursorPageResponse[CommentResponse]:
        cursor_data = decode_cursor(cursor) if cursor else None
        items, has_more = await self.comment_repo.list_comments_cursor(task_id, cursor_data, limit)

        response_items = [
            CommentResponse(
                id=c.id,
                organization_id=c.organization_id,
                task_id=c.task_id,
                author_id=c.author_id,
                author_name=c.author.full_name if c.author else "Unknown",
                author_avatar_url=c.author.avatar_url if c.author else None,
                content=c.content,
                is_edited=c.is_edited,
                created_at=c.created_at,
            )
            for c in items
        ]

        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = encode_cursor(last_item.created_at, last_item.id)

        return CursorPageResponse(
            items=response_items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def update_comment(
        self,
        comment_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: OrgRole,
        payload: CommentUpdate,
    ) -> Comment:
        async with self.uow.transaction():
            comment = await self.comment_repo.get_by_id(comment_id)
            if not comment:
                raise EntityNotFoundException("Comment", comment_id)

            # Only author or Admins/Owners can edit comments
            if comment.author_id != user_id and user_role not in [OrgRole.ADMIN, OrgRole.OWNER]:
                raise ForbiddenOperationException("You are not allowed to edit this comment.")

            comment.content = payload.content.strip()
            comment.is_edited = True
            await self.session.flush()
            return comment
