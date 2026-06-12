import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health_rate_limit(client):
    """Hitting /health 30 times should succeed; the 31st must return 429."""
    for i in range(30):
        resp = await client.get("/health")
        assert resp.status_code == 200, f"Request {i + 1} expected 200, got {resp.status_code}"

    resp = await client.get("/health")
    assert resp.status_code == 429, f"Request 31 expected 429 (rate limited), got {resp.status_code}"
