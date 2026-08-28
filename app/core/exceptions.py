# app/core/exceptions.py
from typing import Any

from fastapi import status


class AppException(Exception):
    """Base class for all business domain errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        title: str = "Internal Application Error",
        type_uri: str = "about:blank",
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.title = title
        self.type_uri = type_uri
        self.extra = extra or {}


class EntityNotFoundException(AppException):
    def __init__(self, entity_name: str, identifier: Any) -> None:
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            title="Entity Not Found",
            type_uri="https://api.saas.platform/errors/not-found",
        )


class EntityConflictException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            title="Resource Conflict",
            type_uri="https://api.saas.platform/errors/conflict",
        )


class ForbiddenOperationException(AppException):
    def __init__(self, message: str = "Access to the requested resource is denied.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden Operation",
            type_uri="https://api.saas.platform/errors/forbidden",
        )
