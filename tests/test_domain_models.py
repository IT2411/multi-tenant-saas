import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityConflictException
from app.models.enums import TaskStatus
from app.models.organization import Organization
from app.models.project import Project
from app.models.user import User
from app.repositories.base import TenantScopedRepository
from app.services.task import TaskService


@pytest.mark.asyncio
async def test_tenant_repository_isolation(db_session: AsyncSession) -> None:
    """Verifies TenantScopedRepository strictly prevents cross-tenant access."""
    # Setup Tenant A & B
    org_a = Organization(name="Acme Corp", slug=f"acme-{uuid.uuid4().hex[:6]}")
    org_b = Organization(name="Stark Corp", slug=f"stark-{uuid.uuid4().hex[:6]}")
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    user = User(
        email=f"tester-{uuid.uuid4().hex[:6]}@domain.com",
        hashed_password="hash",
        full_name="Tester",
    )
    db_session.add(user)
    await db_session.flush()

    proj_a = Project(organization_id=org_a.id, name="Project A", key="PROJA")
    db_session.add(proj_a)
    await db_session.flush()

    # Create Task in Org A
    task_service_a = TaskService(db_session, org_a.id)
    task_a = await task_service_a.create_task(
        project_id=proj_a.id,
        reporter_id=user.id,
        title="Secret Spec",
    )

    # Org B attempts retrieval
    task_repo_b = TenantScopedRepository(Project, db_session, org_b.id)
    retrieved = await task_repo_b.get_by_id(task_a.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_task_optimistic_concurrency_control(db_session: AsyncSession) -> None:
    """Verifies that outdated version updates are rejected with an EntityConflictException."""
    org = Organization(name="OCC Org", slug=f"occ-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()

    user = User(
        email=f"occ-user-{uuid.uuid4().hex[:6]}@domain.com",
        hashed_password="hash",
        full_name="OCC User",
    )
    db_session.add(user)
    await db_session.flush()

    project = Project(organization_id=org.id, name="OCC Project", key="OCC")
    db_session.add(project)
    await db_session.flush()

    task_service = TaskService(db_session, org.id)
    task = await task_service.create_task(
        project_id=project.id,
        reporter_id=user.id,
        title="Concurrent Editing Task",
    )
    assert task.version_id == 1

    # First update succeeds (expected_version=1 -> version_id becomes 2)
    updated_1 = await task_service.update_task_status_occ(
        task_id=task.id,
        actor_id=user.id,
        new_status=TaskStatus.IN_PROGRESS,
        expected_version=1,
    )
    assert updated_1.status == TaskStatus.IN_PROGRESS
    assert updated_1.version_id == 2

    # Second concurrent update with stale expected_version=1 fails
    with pytest.raises(EntityConflictException):
        await task_service.update_task_status_occ(
            task_id=task.id,
            actor_id=user.id,
            new_status=TaskStatus.DONE,
            expected_version=1,
        )
