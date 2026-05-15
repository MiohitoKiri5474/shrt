import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Base

@pytest.fixture(autouse=True)
async def setup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    AsyncTestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async def override_get_db():
        async with AsyncTestSession() as s:
            yield s
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.fixture
async def url_with_clicks(client):
    await client.post("/api/auth/register", json={"email": "s@b.com", "password": "pass1234"})
    login = await client.post("/api/auth/login", data={"username": "s@b.com", "password": "pass1234"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post("/api/urls", json={"original_url": "https://stats.com"}, headers=headers)
    url_data = create.json()
    await client.get(f"/{url_data['short_code']}", follow_redirects=False)
    await client.get(f"/{url_data['short_code']}", follow_redirects=False)
    return url_data["id"], headers

async def test_stats_total_clicks(client, url_with_clicks):
    url_id, headers = url_with_clicks
    resp = await client.get(f"/api/urls/{url_id}/stats", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total_clicks"] == 2

async def test_stats_by_date(client, url_with_clicks):
    url_id, headers = url_with_clicks
    resp = await client.get(f"/api/urls/{url_id}/stats", headers=headers)
    data = resp.json()
    assert len(data["clicks_by_date"]) >= 1

async def test_stats_forbidden_for_non_owner(client, url_with_clicks):
    url_id, _ = url_with_clicks
    await client.post("/api/auth/register", json={"email": "other@b.com", "password": "pass1234"})
    login = await client.post("/api/auth/login", data={"username": "other@b.com", "password": "pass1234"})
    other_token = login.json()["access_token"]
    resp = await client.get(f"/api/urls/{url_id}/stats", headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 403
