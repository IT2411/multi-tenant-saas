import uuid

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityConflictException, EntityNotFoundException
from app.models.audit import AuditLog
from app.models.enums import AuditAction, TaskPriority, TaskStatus
from app.models.task import Task
from app.repositories.base import TenantScopedRepository
from app.services.base import BaseService

logger = structlog.get_logger(__name__)


class TaskService(BaseService):
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        super().__init__(session)
        self.organization_id = organization_id
        self.task_repo = TenantScopedRepository(Task, session, organization_id)

    async def create_task(
        self,
        project_id: uuid.UUID,
        reporter_id: uuid.UUID,
        title: str,
        description: str | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        assignee_id: uuid.UUID | None = None,
    ) -> Task:
        async with self.uow.transaction():
            task = await self.task_repo.create(
                project_id=project_id,
                reporter_id=reporter_id,
                assignee_id=assignee_id,
                title=title,
                description=description,
                status=TaskStatus.BACKLOG,
                priority=priority,
                version_id=1,
            )

            # Record creation in AuditLog
            audit = AuditLog(
                organization_id=self.organization_id,
                actor_id=reporter_id,
                entity_type="Task",
                entity_id=task.id,
                action=AuditAction.CREATE,
                after_state={
                    "title": task.title,
                    "status": task.status.value,
                    "priority": task.priority.value,
                },
            )
            self.session.add(audit)
            return task

    async def update_task_status_occ(
        self,
        task_id: uuid.UUID,
        actor_id: uuid.UUID,
        new_status: TaskStatus,
        expected_version: int,
    ) -> Task:
        """Updates task status using Optimistic Concurrency Control (OCC)."""
        async with self.uow.transaction():
            existing_task = await self.task_repo.get_by_id(task_id)
            if not existing_task:
                raise EntityNotFoundException("Task", task_id)

            before_state = {
                "status": existing_task.status.value,
                "version_id": existing_task.version_id,
            }

            # Atomic conditional update matching expected_version
            stmt = (
                update(Task)
                .where(
                    Task.id == task_id,
                    Task.organization_id == self.organization_id,
                    Task.version_id == expected_version,
                    Task.is_deleted.is_(False),
                )
                .values(
                    status=new_status,
                    version_id=expected_version + 1,
                )
                .returning(Task)
            )
            result = await self.session.execute(stmt)
            updated_task = result.scalar_one_or_none()

            if updated_task is None:
                raise EntityConflictException(
                    f"Conflict updating Task '{task_id}'. Expected version {expected_version}, "
                    f"but record was modified by another concurrent transaction."
                )

            # Record state transition in AuditLog
            audit = AuditLog(
                organization_id=self.organization_id,
                actor_id=actor_id,
                entity_type="Task",
                entity_id=updated_task.id,
                action=AuditAction.UPDATE,
                before_state=before_state,
                after_state={
                    "status": updated_task.status.value,
                    "version_id": updated_task.version_id,
                },
            )
            self.session.add(audit)
            return updated_task
