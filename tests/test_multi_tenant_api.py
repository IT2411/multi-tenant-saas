import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_multi_tenant_project_and_task_lifecycle(client: AsyncClient) -> None:
    # 1. Register Org Alpha
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"alpha-{uuid.uuid4().hex[:6]}@org.com",
            "password": "Password123!",
            "full_name": "Alpha Admin",
            "organization_name": "Alpha Corp",
        },
    )
    assert reg_a.status_code == 201
    token_a = reg_a.json()["access_token"]

    # Fetch Org A ID
    me_a = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    org_a_id = me_a.json()["memberships"][0]["organization_id"]
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Organization-ID": org_a_id}

    # 2. Register Org Beta
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"beta-{uuid.uuid4().hex[:6]}@org.com",
            "password": "Password123!",
            "full_name": "Beta Admin",
            "organization_name": "Beta Corp",
        },
    )
    assert reg_b.status_code == 201
    token_b = reg_b.json()["access_token"]
    me_b = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    org_b_id = me_b.json()["memberships"][0]["organization_id"]
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Organization-ID": org_b_id}

    # 3. Create Project in Org A
    proj_resp = await client.post(
        "/api/v1/projects",
        headers=headers_a,
        json={"name": "Alpha Cloud Platform", "key": "ALPHA"},
    )
    assert proj_resp.status_code == 201
    proj_a_id = proj_resp.json()["id"]

    # 4. Create Task in Org A
    task_resp = await client.post(
        "/api/v1/tasks",
        headers=headers_a,
        json={
            "project_id": proj_a_id,
            "title": "Build Core Engine",
            "priority": "high",
        },
    )
    assert task_resp.status_code == 201
    task_a_id = task_resp.json()["id"]

    # 5. Org B attempts to read Task A (Expect 404 - No cross-tenant leakage)
    spoof_read = await client.get(f"/api/v1/tasks/{task_a_id}", headers=headers_b)
    assert spoof_read.status_code == 404

    # 6. Add Comment in Org A
    comm_resp = await client.post(
        f"/api/v1/tasks/{task_a_id}/comments",
        headers=headers_a,
        json={"content": "Ready for security review"},
    )
    assert comm_resp.status_code == 201

    # 7. Query Task Feed with Cursor Pagination in Org A
    feed_resp = await client.get(
        f"/api/v1/tasks/feed?project_id={proj_a_id}&limit=10",
        headers=headers_a,
    )
    assert feed_resp.status_code == 200
    feed_data = feed_resp.json()
    assert len(feed_data["items"]) == 1
    assert feed_data["has_more"] is False
