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


async def _make_user(email: str, password: str, is_admin: bool = False) -> int:
    async with _AsyncTestSession() as session:
        user = User(email=email, password_hash=hash_password(password), is_admin=is_admin)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


@pytest.fixture
async def admin_cookies(client):
    await _make_user("admin@b.com", "adminpassword123", is_admin=True)
    await client.post(
        "/api/auth/login", data={"username": "admin@b.com", "password": "adminpassword123"}
    )


async def test_list_users_as_admin(client, admin_cookies):
    await _make_user("regular@b.com", "regularpass123")
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert emails == {"admin@b.com", "regular@b.com"}


async def test_list_users_includes_url_count(client, admin_cookies):
    """url_count reflects the number of URLs owned by each user."""
    user_id = await _make_user("owner@b.com", "ownerpass1234")
    async with _AsyncTestSession() as session:
        from app.models import URL

        session.add(URL(user_id=user_id, original_url="https://a.com", short_code="aaa11111"))
        session.add(URL(user_id=user_id, original_url="https://b.com", short_code="bbb22222"))
        await session.commit()
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 200
    by_email = {u["email"]: u for u in resp.json()}
    assert by_email["owner@b.com"]["url_count"] == 2
    assert by_email["admin@b.com"]["url_count"] == 0


async def test_list_users_non_admin_gets_403(client):
    await client.post("/api/auth/register", json={"email": "plain@b.com", "password": "plainpass123"})
    await client.post("/api/auth/login", data={"username": "plain@b.com", "password": "plainpass123"})
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 403


async def test_list_users_unauthenticated_gets_401(client):
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 401


async def test_delete_user_as_admin(client, admin_cookies):
    target_id = await _make_user("target@b.com", "targetpass123")
    resp = await client.delete(f"/api/admin/users/{target_id}")
    assert resp.status_code == 204
    # Confirm the user is gone from the listing.
    listing = await client.get("/api/admin/users")
    emails = {u["email"] for u in listing.json()}
    assert "target@b.com" not in emails


async def test_delete_user_cascades_urls(client, admin_cookies):
    """Deleting a user removes their URLs (and clicks) via relationship cascade."""
    target_id = await _make_user("hasurls@b.com", "haspass12345")
    async with _AsyncTestSession() as session:
        from app.models import URL

        session.add(URL(user_id=target_id, original_url="https://x.com", short_code="xxx11111"))
        await session.commit()
    resp = await client.delete(f"/api/admin/users/{target_id}")
    assert resp.status_code == 204
    async with _AsyncTestSession() as session:
        from sqlalchemy import select
        from app.models import URL

        remaining = await session.execute(select(URL).where(URL.user_id == target_id))
        assert remaining.scalar_one_or_none() is None


async def test_delete_user_non_admin_gets_403(client):
    target_id = await _make_user("victim@b.com", "victimpass123")
    await client.post("/api/auth/register", json={"email": "attacker@b.com", "password": "attackerpass1"})
    await client.post("/api/auth/login", data={"username": "attacker@b.com", "password": "attackerpass1"})
    resp = await client.delete(f"/api/admin/users/{target_id}")
    assert resp.status_code == 403


async def test_delete_user_unauthenticated_gets_401(client):
    target_id = await _make_user("nobody@b.com", "nobodypass123")
    resp = await client.delete(f"/api/admin/users/{target_id}")
    assert resp.status_code == 401


async def test_admin_cannot_delete_self(client, admin_cookies):
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    # Look up the admin id via the listing.
    listing = await client.get("/api/admin/users")
    admin_id = next(u["id"] for u in listing.json() if u["email"] == "admin@b.com")
    resp = await client.delete(f"/api/admin/users/{admin_id}")
    assert resp.status_code == 400


async def test_delete_nonexistent_user_gets_404(client, admin_cookies):
    resp = await client.delete("/api/admin/users/99999")
    assert resp.status_code == 404


async def test_promote_user_to_admin(client, admin_cookies):
    target_id = await _make_user("plain@b.com", "plainpass1234", is_admin=False)
    resp = await client.patch(
        f"/api/admin/users/{target_id}", json={"is_admin": True}
    )
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is True


async def test_demote_admin_to_user(client, admin_cookies):
    target_id = await _make_user("other_admin@b.com", "adminpass1234", is_admin=True)
    resp = await client.patch(
        f"/api/admin/users/{target_id}", json={"is_admin": False}
    )
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is False


async def test_admin_cannot_change_own_role(client, admin_cookies):
    listing = await client.get("/api/admin/users")
    admin_id = next(u["id"] for u in listing.json() if u["email"] == "admin@b.com")
    resp = await client.patch(
        f"/api/admin/users/{admin_id}", json={"is_admin": False}
    )
    assert resp.status_code == 400


async def test_patch_nonexistent_user_gets_404(client, admin_cookies):
    resp = await client.patch("/api/admin/users/99999", json={"is_admin": True})
    assert resp.status_code == 404


async def test_patch_user_non_admin_gets_403(client):
    target_id = await _make_user("victim2@b.com", "victimpass1234")
    await client.post("/api/auth/register", json={"email": "attacker2@b.com", "password": "attackerpass12"})
    await client.post("/api/auth/login", data={"username": "attacker2@b.com", "password": "attackerpass12"})
    resp = await client.patch(
        f"/api/admin/users/{target_id}", json={"is_admin": True}
    )
    assert resp.status_code == 403
