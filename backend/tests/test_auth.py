import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Base, User
from app.services.auth import hash_password

_AsyncTestSession = None

@pytest.fixture(autouse=True)
async def setup_db():
    global _AsyncTestSession
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _AsyncTestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async def override_get_db():
        async with _AsyncTestSession() as s:
            yield s
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    _AsyncTestSession = None
    await engine.dispose()

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.fixture
async def admin_token(client):
    """Create an admin user directly in DB and return its auth cookies."""
    async with _AsyncTestSession() as session:
        admin = User(
            email="admin@b.com",
            password_hash=hash_password("adminpassword123"),
            is_admin=True,
        )
        session.add(admin)
        await session.commit()
    resp = await client.post("/api/auth/login", data={"username": "admin@b.com", "password": "adminpassword123"})
    return dict(resp.cookies)

async def test_register(client):
    resp = await client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123456"})
    assert resp.status_code == 201
    assert resp.json()["email"] == "a@b.com"

async def test_register_duplicate(client):
    await client.post("/api/auth/register", json={"email": "dup@b.com", "password": "secret123456"})
    resp = await client.post("/api/auth/register", json={"email": "dup@b.com", "password": "other12345678"})
    assert resp.status_code == 200

async def test_register_when_disabled(client, monkeypatch):
    monkeypatch.delenv("ALLOW_REGISTRATION", raising=False)
    resp = await client.post("/api/auth/register", json={"email": "d@b.com", "password": "secret123456"})
    assert resp.status_code == 403

async def test_login_success(client):
    await client.post("/api/auth/register", json={"email": "login@b.com", "password": "pass12345678"})
    resp = await client.post("/api/auth/login", data={"username": "login@b.com", "password": "pass12345678"})
    assert resp.status_code == 200
    assert "token_type" in resp.json()
    assert "access_token" not in resp.json()

async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={"email": "x@b.com", "password": "correctpass123"})
    resp = await client.post("/api/auth/login", data={"username": "x@b.com", "password": "wrongpass123"})
    assert resp.status_code == 401

async def test_me_endpoint(client):
    await client.post("/api/auth/register", json={"email": "me@b.com", "password": "pass12345678"})
    login = await client.post("/api/auth/login", data={"username": "me@b.com", "password": "pass12345678"})
    resp = await client.get("/api/auth/me", cookies=login.cookies)
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@b.com"

async def test_invalid_token(client):
    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401

async def test_missing_token(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401

async def test_create_user_as_admin(client, admin_token):
    """Admin users can create new accounts."""
    resp = await client.post(
        "/api/auth/users",
        json={"email": "new@b.com", "password": "newpassword123"},
        cookies=admin_token,
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "new@b.com"

async def test_create_user_non_admin_gets_403(client):
    """Non-admin authenticated users cannot create accounts (403)."""
    await client.post("/api/auth/register", json={"email": "regular@b.com", "password": "regularpass123"})
    login = await client.post("/api/auth/login", data={"username": "regular@b.com", "password": "regularpass123"})
    resp = await client.post(
        "/api/auth/users",
        json={"email": "target@b.com", "password": "targetpass123"},
        cookies=login.cookies,
    )
    assert resp.status_code == 403

async def test_create_user_unauthenticated(client):
    resp = await client.post("/api/auth/users", json={"email": "anon@b.com", "password": "anonpass1234"})
    assert resp.status_code == 401

async def test_create_user_duplicate(client, admin_token):
    await client.post(
        "/api/auth/users",
        json={"email": "dup2@b.com", "password": "pass12345678"},
        cookies=admin_token,
    )
    resp = await client.post(
        "/api/auth/users",
        json={"email": "dup2@b.com", "password": "other12345678"},
        cookies=admin_token,
    )
    assert resp.status_code == 409

async def test_create_user_short_password(client, admin_token):
    resp = await client.post(
        "/api/auth/users",
        json={"email": "short@b.com", "password": "abc"},
        cookies=admin_token,
    )
    assert resp.status_code == 422
