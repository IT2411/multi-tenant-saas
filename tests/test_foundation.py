import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/healthz")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-MS" in response.headers


@pytest.mark.asyncio
async def test_404_rfc7807_error_format(client: AsyncClient) -> None:
    response = await client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["title"] == "HTTP Error" or data["title"] == "Internal Application Error"
    assert "request_id" in data
