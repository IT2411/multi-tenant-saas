import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityConflictException, EntityNotFoundException
from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.base import BaseService


class ProjectService(BaseService):
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        super().__init__(session)
        self.organization_id = organization_id
        self.repo = ProjectRepository(session, organization_id)

    async def create_project(
        self, payload: ProjectCreate, actor_id: uuid.UUID | None = None
    ) -> Project:
        async with self.uow.transaction():
            clean_key = payload.key.upper().strip()
            existing = await self.repo.get_by_key(clean_key)
            if existing:
                raise EntityConflictException(
                    f"Project with key '{clean_key}' already exists in this organization."
                )

            project = await self.repo.create(
                name=payload.name.strip(),
                key=clean_key,
                description=payload.description,
                team_id=payload.team_id,
                is_archived=False,
                version_id=1,
            )

            # Audit record
            audit = AuditLog(
                organization_id=self.organization_id,
                actor_id=actor_id,
                entity_type="Project",
                entity_id=project.id,
                action=AuditAction.CREATE,
                after_state={"name": project.name, "key": project.key},
            )
            self.session.add(audit)
            return project

    async def update_project(
        self,
        project_id: uuid.UUID,
        payload: ProjectUpdate,
        actor_id: uuid.UUID | None = None,
    ) -> Project:
        async with self.uow.transaction():
            project = await self.repo.get_by_id(project_id)
            if not project:
                raise EntityNotFoundException("Project", project_id)

            if project.version_id != payload.expected_version:
                raise EntityConflictException(
                    f"Conflict updating Project '{project_id}'. Expected version {payload.expected_version}, "
                    f"but record was modified by another concurrent transaction (current version: {project.version_id})."
                )

            before_state = {
                "name": project.name,
                "description": project.description,
                "is_archived": project.is_archived,
                "version_id": project.version_id,
            }

            if payload.name is not None:
                project.name = payload.name.strip()
            if payload.description is not None:
                project.description = payload.description
            if payload.team_id is not None:
                project.team_id = payload.team_id
            if payload.is_archived is not None:
                project.is_archived = payload.is_archived

            project.version_id += 1
            await self.session.flush()

            # Audit record
            audit = AuditLog(
                organization_id=self.organization_id,
                actor_id=actor_id,
                entity_type="Project",
                entity_id=project.id,
                action=AuditAction.UPDATE,
                before_state=before_state,
                after_state={
                    "name": project.name,
                    "description": project.description,
                    "is_archived": project.is_archived,
                    "version_id": project.version_id,
                },
            )
            self.session.add(audit)
            return project
