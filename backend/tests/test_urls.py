import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy import update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Base, URL

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

async def test_create_url_custom_code_too_short_rejected(auth_client):
    """custom_code below the 6-char minimum must be rejected (422) — short codes
    are enumerable given the public redirect route's rate limit."""
    resp = await auth_client.post("/api/urls", json={"original_url": "https://short.com", "custom_code": "abc12"})
    assert resp.status_code == 422

async def test_create_url_password_too_short_rejected(auth_client):
    """A URL-protection password below the 6-char minimum must be rejected (422) —
    a 1-char password offers negligible brute-force resistance."""
    resp = await auth_client.post("/api/urls", json={"original_url": "https://secret.com", "password": "abc12"})
    assert resp.status_code == 422

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

async def test_update_url_short_code(auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://edit.com"})
    url_id = create.json()["id"]
    resp = await auth_client.patch(f"/api/urls/{url_id}", json={"short_code": "newcode1"})
    assert resp.status_code == 200
    assert resp.json()["short_code"] == "newcode1"

async def test_update_url_short_code_conflict(auth_client):
    r1 = await auth_client.post("/api/urls", json={"original_url": "https://example.com", "custom_code": "aaacode1"})
    r2 = await auth_client.post("/api/urls", json={"original_url": "https://example.org", "custom_code": "bbbcode1"})
    resp = await auth_client.patch(f"/api/urls/{r2.json()['id']}", json={"short_code": "aaacode1"})
    assert resp.status_code == 409

async def test_update_url_set_password(auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://pw.com"})
    url_id = create.json()["id"]
    resp = await auth_client.patch(f"/api/urls/{url_id}", json={"short_code": create.json()["short_code"], "password": "secret123456"})
    assert resp.status_code == 200
    assert resp.json()["has_password"] is True

async def test_update_url_remove_password(auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://pw2.com"})
    url_id = create.json()["id"]
    code = create.json()["short_code"]
    await auth_client.patch(f"/api/urls/{url_id}", json={"short_code": code, "password": "secret123456"})
    resp = await auth_client.patch(f"/api/urls/{url_id}", json={"short_code": code, "remove_password": True})
    assert resp.status_code == 200
    assert resp.json()["has_password"] is False

async def test_update_url_set_expiry(auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://exp.com"})
    url_id = create.json()["id"]
    code = create.json()["short_code"]
    resp = await auth_client.patch(f"/api/urls/{url_id}", json={"short_code": code, "expires_at": "2099-01-01T00:00:00Z"})
    assert resp.status_code == 200
    assert resp.json()["expires_at"] is not None

async def test_update_url_clear_expiry(auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://exp2.com"})
    url_id = create.json()["id"]
    code = create.json()["short_code"]
    await auth_client.patch(f"/api/urls/{url_id}", json={"short_code": code, "expires_at": "2099-01-01T00:00:00Z"})
    resp = await auth_client.patch(f"/api/urls/{url_id}", json={"short_code": code, "expires_at": None})
    assert resp.status_code == 200
    assert resp.json()["expires_at"] is None

async def test_update_url_not_owner(client, auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://own.com"})
    url_id = create.json()["id"]
    await client.post("/api/auth/register", json={"email": "other2@b.com", "password": "pass12345678"})
    await client.post("/api/auth/login", data={"username": "other2@b.com", "password": "pass12345678"})
    resp = await client.patch(f"/api/urls/{url_id}", json={"short_code": "hacker11"})
    assert resp.status_code == 404

async def test_update_url_not_found(auth_client):
    resp = await auth_client.patch("/api/urls/99999", json={"short_code": "notfound"})
    assert resp.status_code == 404

async def test_create_url_with_password(auth_client):
    resp = await auth_client.post("/api/urls", json={"original_url": "https://secret.com", "password": "hunter2"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["has_password"] is True

async def test_create_url_without_password(auth_client):
    resp = await auth_client.post("/api/urls", json={"original_url": "https://public.com"})
    assert resp.status_code == 201
    assert resp.json()["has_password"] is False

async def test_list_urls_password_flag(auth_client):
    await auth_client.post("/api/urls", json={"original_url": "https://secret.com", "password": "hunter2"})
    await auth_client.post("/api/urls", json={"original_url": "https://public.com"})
    resp = await auth_client.get("/api/urls")
    assert resp.status_code == 200
    items = resp.json()
    assert any(i["has_password"] for i in items)
    assert any(not i["has_password"] for i in items)

async def test_redirect_password_protected_goes_to_gate(client, auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://secret.com", "password": "hunter2"})
    code = create.json()["short_code"]
    resp = await client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == f"/p/{code}"

async def test_unlock_correct_password(client, auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://secret.com", "password": "hunter2"})
    code = create.json()["short_code"]
    resp = await client.post(f"/api/urls/{code}/unlock", json={"password": "hunter2"})
    assert resp.status_code == 200
    assert resp.json()["redirect_url"] == "https://secret.com/"

async def test_unlock_expired_password_protected_returns_410(client, auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://secret.com", "password": "hunter2"})
    code = create.json()["short_code"]
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    agen = app.dependency_overrides[get_db]()
    db = await anext(agen)
    try:
        await db.execute(update(URL).where(URL.short_code == code).values(expires_at=past))
        await db.commit()
    finally:
        await agen.aclose()
    resp = await client.post(f"/api/urls/{code}/unlock", json={"password": "hunter2"})
    assert resp.status_code == 410

async def test_unlock_wrong_password(client, auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://secret.com", "password": "hunter2"})
    code = create.json()["short_code"]
    resp = await client.post(f"/api/urls/{code}/unlock", json={"password": "wrongpw"})
    assert resp.status_code == 401

async def test_unlock_not_password_protected(client, auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://public.com"})
    code = create.json()["short_code"]
    resp = await client.post(f"/api/urls/{code}/unlock", json={"password": "anything"})
    assert resp.status_code == 400

async def test_unlock_not_found(client):
    resp = await client.post("/api/urls/notfound8/unlock", json={"password": "wrongpw"})
    assert resp.status_code == 404

async def test_unlock_records_click(client, auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://secret.com", "password": "hunter2"})
    data = create.json()
    code = data["short_code"]
    url_id = data["id"]
    await client.post(f"/api/urls/{code}/unlock", json={"password": "hunter2"})
    stats = await auth_client.get(f"/api/urls/{url_id}/stats")
    assert stats.json()["total_clicks"] == 1

async def test_redirect_no_click_for_password_protected(client, auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://secret.com", "password": "hunter2"})
    data = create.json()
    code = data["short_code"]
    url_id = data["id"]
    await client.get(f"/{code}", follow_redirects=False)
    stats = await auth_client.get(f"/api/urls/{url_id}/stats")
    assert stats.json()["total_clicks"] == 0

async def test_redirect_expired_link_redirects_to_expired_page(client, auth_client):
    create = await auth_client.post("/api/urls", json={"original_url": "https://example.com"})
    code = create.json()["short_code"]
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    agen = app.dependency_overrides[get_db]()
    db = await anext(agen)
    try:
        await db.execute(update(URL).where(URL.short_code == code).values(expires_at=past))
        await db.commit()
    finally:
        await agen.aclose()
    resp = await client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == f"/expired?code={code}"
