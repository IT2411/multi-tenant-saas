from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

import orjson
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


def orjson_dumps(v: Any, *, default: Any) -> str:
    return orjson.dumps(v, default=default).decode()


class CoreModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class ErrorDetail(CoreModel):
    field: str | None = None
    issue: str


class ProblemDetailResponse(CoreModel):
    """RFC 7807 compliant standardized API error payload."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None
    request_id: str
    invalid_params: list[ErrorDetail] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HealthResponse(CoreModel):
    status: str
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReadinessResponse(CoreModel):
    status: str
    database: bool
    redis: bool
    storage: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StandardResponse(CoreModel, Generic[T]):
    """Unified successful envelope contract."""

    success: bool = True
    data: T
    request_id: str
