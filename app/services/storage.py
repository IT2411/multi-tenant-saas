import uuid
from typing import Any

import aioboto3  # type: ignore[import-untyped]
import structlog
from botocore.client import Config  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.core.config import settings

logger = structlog.get_logger(__name__)


class S3StorageService:
    """Manages secure presigned upload/download interactions with S3/MinIO."""

    def __init__(self) -> None:
        self.session = aioboto3.Session()
        self.bucket = settings.S3_BUCKET_NAME
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.region = settings.S3_REGION_NAME

    def _get_client(self) -> Any:
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    async def ensure_bucket_exists(self) -> None:
        """Verifies or provisions the target storage bucket on application startup."""
        async with self._get_client() as s3:
            try:
                await s3.head_bucket(Bucket=self.bucket)
            except ClientError:
                try:
                    await s3.create_bucket(Bucket=self.bucket)
                    logger.info("s3_bucket_created", bucket=self.bucket)
                except Exception as e:
                    logger.warning("s3_bucket_init_skipped", error=str(e))

    def generate_file_key(
        self, organization_id: uuid.UUID, task_id: uuid.UUID, file_name: str
    ) -> str:
        """Generates tenant-isolated key: org_id/tasks/task_id/uuid_filename."""
        clean_name = file_name.replace(" ", "_")
        return f"{organization_id}/tasks/{task_id}/{uuid.uuid4().hex[:8]}_{clean_name}"

    async def generate_presigned_upload_url(
        self,
        file_key: str,
        content_type: str,
        expires_in_seconds: int = 300,
    ) -> str:
        """Generates a secure presigned PUT URL for direct client upload."""
        async with self._get_client() as s3:
            url = await s3.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": file_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in_seconds,
            )
            return str(url)

    async def generate_presigned_download_url(
        self,
        file_key: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generates a secure presigned GET URL for viewing or downloading files."""
        async with self._get_client() as s3:
            url = await s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": file_key,
                },
                ExpiresIn=expires_in_seconds,
            )
            return str(url)

    async def delete_object(self, file_key: str) -> None:
        """Deletes an object from storage."""
        async with self._get_client() as s3:
            await s3.delete_object(Bucket=self.bucket, Key=file_key)
