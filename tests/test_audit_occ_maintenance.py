import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TaskPriority, TaskStatus
from app.models.organization import Organization
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.workers.tasks import cleanup_soft_deleted_tasks_job


@pytest.mark.asyncio
async def test_audit_logs_query_and_filtering(client: AsyncClient) -> None:
    # 1. Register & setup tenant
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"audit-{uuid.uuid4().hex[:6]}@saas.com",
            "password": "Password123!",
            "full_name": "Audit Admin",
            "organization_name": "Audit Org",
        },
    )
    token = reg_resp.json()["access_token"]
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    org_id = me_resp.json()["memberships"][0]["organization_id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

    # 2. Create Project
    proj = await client.post(
        "/api/v1/projects", headers=headers, json={"name": "Audit Project", "key": "AUD"}
    )
    proj_id = proj.json()["id"]

    # 3. Create Task
    await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"project_id": proj_id, "title": "Audit Task Action"},
    )

    # 4. Query Audit Logs (Requires Admin)
    audit_resp = await client.get("/api/v1/audit-logs?entity_type=Task", headers=headers)
    assert audit_resp.status_code == 200
    data = audit_resp.json()
    assert data["total"] >= 1
    assert data["items"][0]["entity_type"] == "Task"
    assert data["items"][0]["action"] == "CREATE"
    assert "title" in data["items"][0]["after_state"]


@pytest.mark.asyncio
async def test_project_optimistic_concurrency_control(client: AsyncClient) -> None:
    # 1. Setup tenant
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"occ-proj-{uuid.uuid4().hex[:6]}@saas.com",
            "password": "Password123!",
            "full_name": "OCC Proj Admin",
            "organization_name": "OCC Proj Org",
        },
    )
    token = reg_resp.json()["access_token"]
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    org_id = me_resp.json()["memberships"][0]["organization_id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

    # 2. Create Project (starts with version_id = 1)
    proj = await client.post(
        "/api/v1/projects", headers=headers, json={"name": "Concurrent Proj", "key": "CONC"}
    )
    proj_id = proj.json()["id"]
    assert proj.json()["version_id"] == 1

    # 3. Update with correct expected_version=1 (Succeeds -> version becomes 2)
    update_1 = await client.patch(
        f"/api/v1/projects/{proj_id}",
        headers=headers,
        json={"name": "First Update", "expected_version": 1},
    )
    assert update_1.status_code == 200
    assert update_1.json()["version_id"] == 2

    # 4. Stale update with outdated expected_version=1 fails with HTTP 409 Conflict
    update_conflict = await client.patch(
        f"/api/v1/projects/{proj_id}",
        headers=headers,
        json={"name": "Stale Update", "expected_version": 1},
    )
    assert update_conflict.status_code == 409


@pytest.mark.asyncio
async def test_soft_delete_maintenance_sweeper(db_session: AsyncSession) -> None:
    # 1. Create Organization & User
    org = Organization(name="Sweeper Org", slug=f"sweep-{uuid.uuid4().hex[:6]}")
    user = User(
        email=f"sweep-{uuid.uuid4().hex[:6]}@domain.com",
        hashed_password="hash",
        full_name="Sweeper User",
    )
    db_session.add_all([org, user])
    await db_session.flush()

    # 2. Create Project
    project = Project(
        organization_id=org.id,
        name="Sweeper Project",
        key=f"SW{uuid.uuid4().hex[:2].upper()}",
        version_id=1,
    )
    db_session.add(project)
    await db_session.flush()

    # 3. Create expired soft-deleted task (> 30 days old)
    expired_deleted_at = datetime.now(UTC) - timedelta(days=35)
    expired_task = Task(
        id=uuid.uuid4(),
        organization_id=org.id,
        project_id=project.id,
        reporter_id=user.id,
        title="Old Deleted Task",
        status=TaskStatus.DONE,
        priority=TaskPriority.LOW,
        version_id=1,
        is_deleted=True,
        deleted_at=expired_deleted_at,
    )
    db_session.add(expired_task)
    await db_session.commit()

    # 4. Execute maintenance sweeper job
    purged_count = await cleanup_soft_deleted_tasks_job({}, days_threshold=30)
    assert purged_count >= 1
