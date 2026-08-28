import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import CoreModel


class CommentCreate(CoreModel):
    content: str = Field(min_length=1, max_length=10000)


class CommentUpdate(CoreModel):
    content: str = Field(min_length=1, max_length=10000)


class CommentResponse(CoreModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    task_id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    author_avatar_url: str | None
    content: str
    is_edited: bool
    created_at: datetime
