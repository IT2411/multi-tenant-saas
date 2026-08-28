import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column


def utc_now() -> datetime:
    """Standardized UTC timestamp generator."""
    return datetime.now(UTC)


class UUIDPrimaryKeyMixin:
    """Standard RFC 4122 v4 UUID Primary Key."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        sort_order=-100,
    )


class TimestampMixin:
    """Time-tracking mixin providing creation and update timestamps in UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SoftDeleteMixin:
    """Supports non-destructive logical deletion."""

    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantScopedMixin:
    """Enforces association with an organization tenant."""

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
        sort_order=-90,
    )
