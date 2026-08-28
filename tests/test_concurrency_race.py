import asyncio
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_high_concurrency_optimistic_locking_race(client: AsyncClient) -> None:
    """Fires 10 simultaneous updates with the same expected_version.

    Exactly ONE must succeed (200), and the remaining 9 must fail with 409 Conflict.
    """
    # 1. Setup tenant & project
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"race-{uuid.uuid4().hex[:6]}@saas.com",
            "password": "Password123!",
            "full_name": "Race Tester",
            "organization_name": "Race Org",
        },
    )
    token = reg_resp.json()["access_token"]
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    org_id = me_resp.json()["memberships"][0]["organization_id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

    proj_resp = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Race Condition Project", "key": "RACE"},
    )
    proj_id = proj_resp.json()["id"]

    # 2. Create Task (Initial version_id = 1)
    task_resp = await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"project_id": proj_id, "title": "Concurrent Task Target", "priority": "medium"},
    )
    task_id = task_resp.json()["id"]
    assert task_resp.json()["version_id"] == 1

    # 3. Fire 10 simultaneous concurrent patch requests competing with expected_version = 1
    async def send_concurrent_update(i: int):
        return await client.patch(
            f"/api/v1/tasks/{task_id}",
            headers=headers,
            json={
                "title": f"Concurrent Update Attempt {i}",
                "status": "in_progress",
                "expected_version": 1,
            },
        )

    tasks = [send_concurrent_update(i) for i in range(10)]
    responses = await asyncio.gather(*tasks)

    # 4. Assert that exactly ONE update won the race, and 9 were safely rejected
    status_codes = [r.status_code for r in responses]
    success_count = status_codes.count(200)
    conflict_count = status_codes.count(409)

    assert success_count == 1
    assert conflict_count == 9

    # 5. Verify final version is 2
    final_task_resp = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert final_task_resp.status_code == 200
    assert final_task_resp.json()["version_id"] == 2
