import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_probe(client: AsyncClient) -> None:
    response = await client.get("/api/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_probe(client: AsyncClient) -> None:
    response = await client.get("/api/v1/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] is True
    assert data["redis"] is True
    assert data["storage"] is True


@pytest.mark.asyncio
async def test_prometheus_metrics_scrape_endpoint(client: AsyncClient) -> None:
    response = await client.get("/metrics")
    assert response.status_code == 200
    metrics_output = response.text
    # Verify standard Prometheus metrics are exposed
    assert (
        "http_requests_total" in metrics_output or "http_request_duration_seconds" in metrics_output
    )
