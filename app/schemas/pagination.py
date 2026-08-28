from typing import Generic, TypeVar

from app.schemas.common import CoreModel

T = TypeVar("T")


class OffsetPageResponse(CoreModel, Generic[T]):
    """Standard envelope for offset-based pagination."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class CursorPageResponse(CoreModel, Generic[T]):
    """Standard envelope for keyset/cursor-based pagination."""

    items: list[T]
    next_cursor: str | None = None
    has_more: bool
