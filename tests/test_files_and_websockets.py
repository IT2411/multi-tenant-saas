import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_presigned_attachment_url_generation(client: AsyncClient) -> None:
    # 1. Register & setup tenant
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"storage-{uuid.uuid4().hex[:6]}@saas.com",
            "password": "Password123!",
            "full_name": "Storage User",
            "organization_name": "Storage Org",
        },
    )
    token = reg_resp.json()["access_token"]
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    org_id = me_resp.json()["memberships"][0]["organization_id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

    # 2. Create Project & Task
    proj = await client.post(
        "/api/v1/projects", headers=headers, json={"name": "Files Project", "key": "FILE"}
    )
    proj_id = proj.json()["id"]

    task = await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"project_id": proj_id, "title": "Implement File Storage"},
    )
    task_id = task.json()["id"]

    # 3. Request Presigned Upload URL
    presign_resp = await client.post(
        f"/api/v1/tasks/{task_id}/attachments/presigned-upload",
        headers=headers,
        json={
            "file_name": "architecture_diagram.png",
            "file_size": 2048576,
            "content_type": "image/png",
        },
    )
    assert presign_resp.status_code == 200
    presign_data = presign_resp.json()
    assert "upload_url" in presign_data
    assert "file_key" in presign_data
    assert presign_data["file_key"].startswith(f"{org_id}/tasks/{task_id}/")

    # 4. Confirm Attachment Upload
    confirm_resp = await client.post(
        f"/api/v1/tasks/{task_id}/attachments",
        headers=headers,
        json={
            "file_name": "architecture_diagram.png",
            "file_size": 2048576,
            "content_type": "image/png",
            "s3_key": presign_data["file_key"],
        },
    )
    assert confirm_resp.status_code == 201
    attachment_data = confirm_resp.json()
    assert attachment_data["file_name"] == "architecture_diagram.png"
    assert "download_url" in attachment_data
