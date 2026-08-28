import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityConflictException, EntityNotFoundException
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.base import BaseService


class ProjectService(BaseService):
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        super().__init__(session)
        self.organization_id = organization_id
        self.repo = ProjectRepository(session, organization_id)

    async def create_project(self, payload: ProjectCreate) -> Project:
        async with self.uow.transaction():
            clean_key = payload.key.upper().strip()
            existing = await self.repo.get_by_key(clean_key)
            if existing:
                raise EntityConflictException(
                    f"Project with key '{clean_key}' already exists in this organization."
                )

            return await self.repo.create(
                name=payload.name.strip(),
                key=clean_key,
                description=payload.description,
                team_id=payload.team_id,
                is_archived=False,
            )

    async def update_project(self, project_id: uuid.UUID, payload: ProjectUpdate) -> Project:
        async with self.uow.transaction():
            project = await self.repo.get_by_id(project_id)
            if not project:
                raise EntityNotFoundException("Project", project_id)

            if payload.name is not None:
                project.name = payload.name.strip()
            if payload.description is not None:
                project.description = payload.description
            if payload.team_id is not None:
                project.team_id = payload.team_id
            if payload.is_archived is not None:
                project.is_archived = payload.is_archived

            await self.session.flush()
            return project
