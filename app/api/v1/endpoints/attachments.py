import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireRole, TenantContext, get_db_session
from app.core.exceptions import EntityNotFoundException
from app.models.enums import OrgRole
from app.repositories.attachment import AttachmentRepository
from app.repositories.task import TaskRepository
from app.schemas.attachment import (
    AttachmentConfirmCreate,
    AttachmentResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.services.storage import S3StorageService

router = APIRouter(prefix="/tasks/{task_id}/attachments", tags=["Attachments"])


@router.post(
    "/presigned-upload",
    response_model=PresignedUploadResponse,
    summary="Generate presigned S3/MinIO upload URL for attachment",
)
async def generate_upload_url(
    task_id: uuid.UUID,
    payload: PresignedUploadRequest,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.MEMBER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PresignedUploadResponse:
    task_repo = TaskRepository(session, ctx.organization_id)
    task = await task_repo.get_by_id(task_id)
    if not task:
        raise EntityNotFoundException("Task", task_id)

    storage = S3StorageService()
    file_key = storage.generate_file_key(ctx.organization_id, task_id, payload.file_name)
    upload_url = await storage.generate_presigned_upload_url(file_key, payload.content_type)

    return PresignedUploadResponse(
        upload_url=upload_url,
        file_key=file_key,
        expires_in=300,
    )


@router.post(
    "",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm attachment upload and store metadata",
)
async def confirm_attachment(
    task_id: uuid.UUID,
    payload: AttachmentConfirmCreate,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.MEMBER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AttachmentResponse:
    task_repo = TaskRepository(session, ctx.organization_id)
    task = await task_repo.get_by_id(task_id)
    if not task:
        raise EntityNotFoundException("Task", task_id)

    repo = AttachmentRepository(session, ctx.organization_id)
    attachment = await repo.create(
        task_id=task_id,
        uploader_id=ctx.user.id,
        file_name=payload.file_name,
        file_size=payload.file_size,
        content_type=payload.content_type,
        s3_key=payload.s3_key,
    )
    await session.commit()

    storage = S3StorageService()
    download_url = await storage.generate_presigned_download_url(attachment.s3_key)

    return AttachmentResponse(
        id=attachment.id,
        organization_id=attachment.organization_id,
        task_id=attachment.task_id,
        uploader_id=attachment.uploader_id,
        file_name=attachment.file_name,
        file_size=attachment.file_size,
        content_type=attachment.content_type,
        download_url=download_url,
        created_at=attachment.created_at,
    )


@router.get(
    "",
    response_model=list[AttachmentResponse],
    summary="List all attachments for a task with fresh presigned download URLs",
)
async def list_attachments(
    task_id: uuid.UUID,
    ctx: Annotated[TenantContext, Depends(RequireRole(OrgRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[AttachmentResponse]:
    repo = AttachmentRepository(session, ctx.organization_id)
    attachments = await repo.list_by_task(task_id)
    storage = S3StorageService()

    results: list[AttachmentResponse] = []
    for att in attachments:
        download_url = await storage.generate_presigned_download_url(att.s3_key)
        results.append(
            AttachmentResponse(
                id=att.id,
                organization_id=att.organization_id,
                task_id=att.task_id,
                uploader_id=att.uploader_id,
                file_name=att.file_name,
                file_size=att.file_size,
                content_type=att.content_type,
                download_url=download_url,
                created_at=att.created_at,
            )
        )
    return results
