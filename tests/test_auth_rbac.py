import uuid

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireRole
from app.models.enums import OrgRole
from app.models.organization import Organization, OrganizationMember
from app.models.user import User


@pytest.mark.asyncio
async def test_user_registration_and_login_flow(client: AsyncClient) -> None:
    email = f"developer-{uuid.uuid4().hex[:6]}@example.com"
    password = "SuperSecretPassword123!"
    full_name = "Jane Developer"

    # 1. Register
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "organization_name": "Jane Labs",
        },
    )
    assert reg_resp.status_code == 201
    tokens = reg_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 2. Access /auth/me with Bearer token
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    assert user_data["email"] == email
    assert len(user_data["memberships"]) == 1
    assert user_data["memberships"][0]["role"] == "owner"

    # 3. Refresh Token
    ref_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_resp.status_code == 200
    new_tokens = ref_resp.json()
    assert new_tokens["access_token"] != access_token

    # 4. Old refresh token should now be rejected (Token Rotation)
    stale_ref_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert stale_ref_resp.status_code == 401

    # 5. Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert logout_resp.status_code == 204


@pytest.mark.asyncio
async def test_rbac_role_hierarchy(db_session: AsyncSession) -> None:
    """Verifies that an ADMIN can access admin-protected resources while a VIEWER is rejected with 403."""
    org = Organization(name="RBAC Testing Org", slug=f"rbac-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()

    admin_user = User(
        email=f"admin-{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hash",
        full_name="Admin User",
    )
    viewer_user = User(
        email=f"viewer-{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hash",
        full_name="Viewer User",
    )
    db_session.add_all([admin_user, viewer_user])
    await db_session.flush()

    db_session.add_all(
        [
            OrganizationMember(organization_id=org.id, user_id=admin_user.id, role=OrgRole.ADMIN),
            OrganizationMember(organization_id=org.id, user_id=viewer_user.id, role=OrgRole.VIEWER),
        ]
    )
    await db_session.flush()

    admin_guard = RequireRole(min_role=OrgRole.ADMIN)

    # Admin passes
    ctx = await admin_guard(
        current_user=admin_user,
        session=db_session,
        x_organization_id=org.id,
    )
    assert ctx.role == OrgRole.ADMIN

    # Viewer fails with 403
    with pytest.raises(HTTPException) as exc_info:
        await admin_guard(
            current_user=viewer_user,
            session=db_session,
            x_organization_id=org.id,
        )
    assert exc_info.value.status_code == 403
