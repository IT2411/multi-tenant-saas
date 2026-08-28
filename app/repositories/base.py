import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar, cast

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository providing decoupled async data-access operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelType | None:
        return await self.session.get(self.model, entity_id)

    async def create(self, **attributes: Any) -> ModelType:
        instance = self.model(**attributes)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.session.delete(instance)
        await self.session.flush()


class TenantScopedRepository(BaseRepository[ModelType]):
    """Enforces tenant isolation across all query filters and write operations."""

    def __init__(
        self,
        model: type[ModelType],
        session: AsyncSession,
        organization_id: uuid.UUID,
    ) -> None:
        super().__init__(model, session)
        self.organization_id = organization_id

    @property
    def _model_entity(self) -> Any:
        return cast("Any", self.model)

    async def get_by_id(
        self,
        entity_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> ModelType | None:
        stmt = select(self.model).where(
            self._model_entity.id == entity_id,
            self._model_entity.organization_id == self.organization_id,
        )
        if not include_deleted and hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self._model_entity.is_deleted.is_(False))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
    ) -> Sequence[ModelType]:
        stmt = select(self.model).where(self._model_entity.organization_id == self.organization_id)
        if not include_deleted and hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self._model_entity.is_deleted.is_(False))

        stmt = stmt.offset(offset).limit(min(limit, 100))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, include_deleted: bool = False) -> int:
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self._model_entity.organization_id == self.organization_id)
        )
        if not include_deleted and hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self._model_entity.is_deleted.is_(False))

        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def create(self, **attributes: Any) -> ModelType:
        attributes["organization_id"] = self.organization_id
        return await super().create(**attributes)

    async def soft_delete(self, entity_id: uuid.UUID) -> bool:
        if not hasattr(self.model, "is_deleted"):
            raise TypeError(f"Model {self.model.__name__} does not support soft deletion")

        stmt = (
            update(self.model)
            .where(
                self._model_entity.id == entity_id,
                self._model_entity.organization_id == self.organization_id,
                self._model_entity.is_deleted.is_(False),
            )
            .values(is_deleted=True, deleted_at=func.now())
            .returning(self._model_entity.id)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none() is not None
