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
async def auth_client(client):
    await client.post("/api/auth/register", json={"email": "owner@b.com", "password": "pass12345678"})
    await client.post("/api/auth/login", data={"username": "owner@b.com", "password": "pass12345678"})
    return client

async def test_create_url(auth_client):
    resp = await auth_client.post("/api/urls", json={"original_url": "https://example.com"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["original_url"] == "https://example.com/"
    assert len(data["short_code"]) == 8

async def test_list_urls(auth_client):
    await auth_client.post("/api/urls", json={"original_url": "https://example.com"})
    await auth_client.post("/api/urls", json={"original_url": "https://example.org"})
    resp = await auth_client.get("/api/urls")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

async def test_delete_url(auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://del.com"})
    url_id = create.json()["id"]
    resp = await auth_client.delete(f"/api/urls/{url_id}")
    assert resp.status_code == 204

async def test_delete_url_not_owner(client, auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://priv.com"})
    url_id = create.json()["id"]
    await client.post("/api/auth/register", json={"email": "other@b.com", "password": "pass12345678"})
    await client.post("/api/auth/login", data={"username": "other@b.com", "password": "pass12345678"})
    resp = await client.delete(f"/api/urls/{url_id}")
    assert resp.status_code == 404

async def test_redirect(client, auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://example.com"})
    code = create.json()["short_code"]
    resp = await client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/"

async def test_redirect_not_found(client):
    resp = await client.get("/notfound8", follow_redirects=False)
    assert resp.status_code == 404

async def test_create_url_custom_code(auth_client):
    resp = await auth_client.post("/api/urls", json={"original_url": "https://custom.com", "custom_code": "mycode1"})
    assert resp.status_code == 201
    assert resp.json()["short_code"] == "mycode1"

async def test_create_url_custom_code_conflict(auth_client):
    await auth_client.post("/api/urls", json={"original_url": "https://example.com", "custom_code": "taken123"})
    resp = await auth_client.post("/api/urls", json={"original_url": "https://example.org", "custom_code": "taken123"})
    assert resp.status_code == 409

async def test_delete_url_not_found(auth_client):
    resp = await auth_client.delete("/api/urls/99999")
    assert resp.status_code == 404

async def test_stats_not_found(auth_client):
    resp = await auth_client.get("/api/urls/99999/stats")
    assert resp.status_code == 404

async def test_qr_code_success(auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://qr.com"})
    code = create.json()["short_code"]
    resp = await auth_client.get(f"/api/urls/{code}/qr")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"

async def test_qr_code_not_found(auth_client):
    resp = await auth_client.get("/api/urls/nosuchcode/qr")
    assert resp.status_code == 404

async def test_qr_code_requires_auth(client):
    resp = await client.get("/api/urls/anycode/qr")
    assert resp.status_code == 401

async def test_qr_code_not_owner(client, auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://owned.com"})
    code = create.json()["short_code"]
    await client.post("/api/auth/register", json={"email": "intruder@b.com", "password": "pass12345678"})
    await client.post("/api/auth/login", data={"username": "intruder@b.com", "password": "pass12345678"})
    resp = await client.get(f"/api/urls/{code}/qr")
    assert resp.status_code == 404
