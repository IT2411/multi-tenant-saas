import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_cross_tenant_header_spoofing_defense(client: AsyncClient) -> None:
    """Verifies that User A cannot access Org B resources by forging the X-Organization-ID header."""
    # 1. Register Org A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"attacker-{uuid.uuid4().hex[:6]}@org-a.com",
            "password": "Password123!",
            "full_name": "Attacker A",
            "organization_name": "Org Alpha",
        },
    )
    token_a = reg_a.json()["access_token"]

    # 2. Register Org B
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"victim-{uuid.uuid4().hex[:6]}@org-b.com",
            "password": "Password123!",
            "full_name": "Victim B",
            "organization_name": "Org Beta",
        },
    )
    token_b = reg_b.json()["access_token"]
    me_b = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    org_b_id = me_b.json()["memberships"][0]["organization_id"]

    # 3. Attacker A attempts to perform a request with their token against Org B's ID
    spoof_resp = await client.get(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {token_a}", "X-Organization-ID": org_b_id},
    )
    assert spoof_resp.status_code == 403
    assert "not a member" in spoof_resp.json()["detail"]


@pytest.mark.asyncio
async def test_rbac_privilege_escalation_defense(client: AsyncClient) -> None:
    """Verifies that a VIEWER member cannot create projects or invite members."""
    # 1. Register Owner
    reg_owner = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"owner-{uuid.uuid4().hex[:6]}@rbac.com",
            "password": "Password123!",
            "full_name": "Owner User",
            "organization_name": "RBAC Org",
        },
    )
    owner_token = reg_owner.json()["access_token"]
    me_owner = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {owner_token}"}
    )
    org_id = me_owner.json()["memberships"][0]["organization_id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Organization-ID": org_id}

    # 2. Register Viewer User
    viewer_email = f"viewer-{uuid.uuid4().hex[:6]}@rbac.com"
    reg_viewer = await client.post(
        "/api/v1/auth/register",
        json={
            "email": viewer_email,
            "password": "Password123!",
            "full_name": "Viewer User",
            "organization_name": "Viewer Solo Org",
        },
    )
    viewer_token = reg_viewer.json()["access_token"]

    # 3. Owner invites Viewer User into RBAC Org as VIEWER
    await client.post(
        "/api/v1/organizations/current/members/invite",
        headers=owner_headers,
        json={"email": viewer_email, "role": "viewer"},
    )

    viewer_headers = {"Authorization": f"Bearer {viewer_token}", "X-Organization-ID": org_id}

    # 4. Viewer attempts to create a project (Requires MANAGER) -> Expect 403
    escalate_proj = await client.post(
        "/api/v1/projects",
        headers=viewer_headers,
        json={"name": "Illegal Project", "key": "ILLEGAL"},
    )
    assert escalate_proj.status_code == 403
    assert "Insufficient permissions" in escalate_proj.json()["detail"]

    # 5. Viewer attempts to invite another user (Requires ADMIN) -> Expect 403
    escalate_invite = await client.post(
        "/api/v1/organizations/current/members/invite",
        headers=viewer_headers,
        json={"email": "hacker@test.com", "role": "admin"},
    )
    assert escalate_invite.status_code == 403


@pytest.mark.asyncio
async def test_jwt_tampering_and_type_confusion_defense(client: AsyncClient) -> None:
    """Verifies that tampered, expired, or type-confused tokens are strictly rejected."""
    # 1. Register User
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"jwt-test-{uuid.uuid4().hex[:6]}@saas.com",
            "password": "Password123!",
            "full_name": "JWT Tester",
            "organization_name": "JWT Test Org",
        },
    )
    tokens = reg_resp.json()
    valid_access = tokens["access_token"]
    valid_refresh = tokens["refresh_token"]

    # 2. Tampered Signature Attack
    tampered_token = valid_access[:-5] + "XXXXX"
    tamper_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert tamper_resp.status_code == 401

    # 3. Token Type Confusion Attack: Use a REFRESH token as a Bearer ACCESS token
    type_confusion_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {valid_refresh}"},
    )
    assert type_confusion_resp.status_code == 401

    # 4. Token with Expired Timestamp
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "jti": str(uuid.uuid4()),
        "type": "access",
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "iat": datetime.now(UTC) - timedelta(hours=2),
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm="HS256")
    expired_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired_resp.status_code == 401


@pytest.mark.asyncio
async def test_sql_injection_and_malformed_payload_defense(client: AsyncClient) -> None:
    """Verifies parameterized query isolation and Pydantic input boundary enforcement."""
    # 1. Setup tenant
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"sqli-{uuid.uuid4().hex[:6]}@saas.com",
            "password": "Password123!",
            "full_name": "SQLi Tester",
            "organization_name": "SQLi Org",
        },
    )
    token = reg_resp.json()["access_token"]
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    org_id = me_resp.json()["memberships"][0]["organization_id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

    # 2. SQL Injection vector in Task Search parameter
    sqli_search = "' OR 1=1; DROP TABLE tasks; --"
    search_resp = await client.get(
        f"/api/v1/tasks?search={sqli_search}",
        headers=headers,
    )
    assert search_resp.status_code == 200
    assert search_resp.json()["items"] == []

    # 3. Malformed / Oversized Payload (Exceeding max_length=10 on Project Key)
    oversized_key_resp = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Valid Name", "key": "THISKEYISTOOLONGFORSCHEMA"},
    )
    assert oversized_key_resp.status_code == 422
    assert "invalid_params" in oversized_key_resp.json()
