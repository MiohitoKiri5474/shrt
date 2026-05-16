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

async def test_register(client):
    resp = await client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    assert resp.status_code == 201
    assert resp.json()["email"] == "a@b.com"

async def test_register_duplicate(client):
    await client.post("/api/auth/register", json={"email": "dup@b.com", "password": "secret123"})
    resp = await client.post("/api/auth/register", json={"email": "dup@b.com", "password": "other123"})
    assert resp.status_code == 409

async def test_login_success(client):
    await client.post("/api/auth/register", json={"email": "login@b.com", "password": "pass1234"})
    resp = await client.post("/api/auth/login", data={"username": "login@b.com", "password": "pass1234"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={"email": "x@b.com", "password": "correct"})
    resp = await client.post("/api/auth/login", data={"username": "x@b.com", "password": "wrong"})
    assert resp.status_code == 401

async def test_me_endpoint(client):
    await client.post("/api/auth/register", json={"email": "me@b.com", "password": "pass1234"})
    login = await client.post("/api/auth/login", data={"username": "me@b.com", "password": "pass1234"})
    token = login.json()["access_token"]
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@b.com"

async def test_invalid_token(client):
    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401

async def test_missing_token(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401

async def _get_token(client, email: str = "admin@b.com", password: str = "secret123") -> str:
    await client.post("/api/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/auth/login", data={"username": email, "password": password})
    return resp.json()["access_token"]

async def test_create_user_authenticated(client):
    token = await _get_token(client)
    resp = await client.post(
        "/api/auth/users",
        json={"email": "new@b.com", "password": "newpass1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "new@b.com"

async def test_create_user_unauthenticated(client):
    resp = await client.post("/api/auth/users", json={"email": "anon@b.com", "password": "anon1234"})
    assert resp.status_code == 401

async def test_create_user_duplicate(client):
    token = await _get_token(client)
    await client.post(
        "/api/auth/users",
        json={"email": "dup2@b.com", "password": "pass1234"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.post(
        "/api/auth/users",
        json={"email": "dup2@b.com", "password": "other123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409

async def test_create_user_short_password(client):
    token = await _get_token(client)
    resp = await client.post(
        "/api/auth/users",
        json={"email": "short@b.com", "password": "abc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
