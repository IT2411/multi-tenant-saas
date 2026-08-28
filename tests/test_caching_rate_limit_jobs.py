import uuid

import pytest
from httpx import AsyncClient

from app.core.cache import CacheService
from app.schemas.project import ProjectResponse


@pytest.mark.asyncio
async def test_cache_hit_and_invalidation_lifecycle(client: AsyncClient) -> None:
    # 1. Register and setup tenant
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"cache-{uuid.uuid4().hex[:6]}@saas.com",
            "password": "Password123!",
            "full_name": "Cache User",
            "organization_name": "Cache Org",
        },
    )
    token = reg_resp.json()["access_token"]
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    org_id = me_resp.json()["memberships"][0]["organization_id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

    # 2. Create Project
    proj_resp = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Cache Test Project", "key": "CACHE"},
    )
    proj_id = proj_resp.json()["id"]

    # 3. First read (Cache Miss -> Sets Redis Cache)
    read_1 = await client.get(f"/api/v1/projects/{proj_id}", headers=headers)
    assert read_1.status_code == 200

    cache_key = CacheService.build_key("tenant", str(org_id), "projects", str(proj_id))
    cached = await CacheService.get(cache_key, ProjectResponse)
    assert cached is not None
    assert cached.name == "Cache Test Project"

    # 4. Update Project with OCC expected_version (Triggers Cache Invalidation)
    update_resp = await client.patch(
        f"/api/v1/projects/{proj_id}",
        headers=headers,
        json={"name": "Updated Cache Project", "expected_version": 1},
    )
    assert update_resp.status_code == 200

    # 5. Verify cache key was evicted
    cached_after_update = await CacheService.get(cache_key, ProjectResponse)
    assert cached_after_update is None


@pytest.mark.asyncio
async def test_sliding_window_rate_limiting(client: AsyncClient) -> None:
    email = f"ratelimit-{uuid.uuid4().hex[:6]}@saas.com"
    payload = {"email": email, "password": "WrongPassword"}

    responses = []
    for _ in range(6):
        res = await client.post("/api/v1/auth/login", json=payload)
        responses.append(res)

    assert responses[-1].status_code == 429
    assert "Retry-After" in responses[-1].headers
    assert "X-RateLimit-Limit" in responses[-1].headers
    assert responses[-1].headers["X-RateLimit-Remaining"] == "0"
