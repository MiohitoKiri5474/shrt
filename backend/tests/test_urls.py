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
async def auth_headers(client):
    await client.post("/api/auth/register", json={"email": "owner@b.com", "password": "pass1234"})
    resp = await client.post("/api/auth/login", data={"username": "owner@b.com", "password": "pass1234"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

async def test_create_url(client, auth_headers):
    resp = await client.post("/api/urls", json={"original_url": "https://example.com"}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["original_url"] == "https://example.com"
    assert len(data["short_code"]) == 8

async def test_list_urls(client, auth_headers):
    await client.post("/api/urls", json={"original_url": "https://a.com"}, headers=auth_headers)
    await client.post("/api/urls", json={"original_url": "https://b.com"}, headers=auth_headers)
    resp = await client.get("/api/urls", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

async def test_delete_url(client, auth_headers):
    create = await client.post("/api/urls", json={"original_url": "https://del.com"}, headers=auth_headers)
    url_id = create.json()["id"]
    resp = await client.delete(f"/api/urls/{url_id}", headers=auth_headers)
    assert resp.status_code == 204

async def test_delete_url_not_owner(client, auth_headers):
    create = await client.post("/api/urls", json={"original_url": "https://priv.com"}, headers=auth_headers)
    url_id = create.json()["id"]
    await client.post("/api/auth/register", json={"email": "other@b.com", "password": "pass1234"})
    other_login = await client.post("/api/auth/login", data={"username": "other@b.com", "password": "pass1234"})
    other_token = other_login.json()["access_token"]
    resp = await client.delete(f"/api/urls/{url_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 403

async def test_redirect(client, auth_headers):
    create = await client.post("/api/urls", json={"original_url": "https://redirect.com"}, headers=auth_headers)
    code = create.json()["short_code"]
    resp = await client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://redirect.com"

async def test_redirect_not_found(client):
    resp = await client.get("/nonexistent-short-code", follow_redirects=False)
    assert resp.status_code == 404

async def test_create_url_custom_code(client, auth_headers):
    resp = await client.post("/api/urls", json={"original_url": "https://custom.com", "custom_code": "mycode1"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["short_code"] == "mycode1"

async def test_create_url_custom_code_conflict(client, auth_headers):
    await client.post("/api/urls", json={"original_url": "https://a.com", "custom_code": "taken123"}, headers=auth_headers)
    resp = await client.post("/api/urls", json={"original_url": "https://b.com", "custom_code": "taken123"}, headers=auth_headers)
    assert resp.status_code == 409

async def test_delete_url_not_found(client, auth_headers):
    resp = await client.delete("/api/urls/99999", headers=auth_headers)
    assert resp.status_code == 404

async def test_stats_not_found(client, auth_headers):
    resp = await client.get("/api/urls/99999/stats", headers=auth_headers)
    assert resp.status_code == 404
