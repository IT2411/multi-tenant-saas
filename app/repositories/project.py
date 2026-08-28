import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.base import TenantScopedRepository


class ProjectRepository(TenantScopedRepository[Project]):
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        super().__init__(Project, session, organization_id)

    async def get_by_key(self, key: str) -> Project | None:
        stmt = select(Project).where(
            Project.organization_id == self.organization_id,
            Project.key == key.upper().strip(),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
