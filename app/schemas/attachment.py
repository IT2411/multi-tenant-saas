import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import CoreModel


class PresignedUploadRequest(CoreModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_size: int = Field(gt=0, le=52428800)  # Max 50 MB
    content_type: str = Field(min_length=3, max_length=100)


class PresignedUploadResponse(CoreModel):
    upload_url: str
    file_key: str
    expires_in: int


class AttachmentConfirmCreate(CoreModel):
    file_name: str
    file_size: int
    content_type: str
    s3_key: str


class AttachmentResponse(CoreModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    task_id: uuid.UUID
    uploader_id: uuid.UUID
    file_name: str
    file_size: int
    content_type: str
    download_url: str | None = None
    created_at: datetime
