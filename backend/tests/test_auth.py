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
    resp = await client.post("/api/auth/register", json={"email": "dup@b.com", "password": "other"})
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
