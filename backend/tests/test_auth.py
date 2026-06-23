import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Base, User
from app.services.auth import hash_password
from app.services.token_blocklist import get_token_blocklist

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
    assert resp.status_code == 409

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


# --- SHA-256 prehash regression and length-guard tests ---

async def test_prehash_72_vs_73_char_passwords_do_not_match():
    """Regression guard for bcrypt's silent 72-byte truncation bug.

    Before the SHA-256 prehash fix, bcrypt truncated input at byte 72, so a
    72-char password and a 73-char password that shared the first 72 bytes
    would hash to effectively the same value.  With prehash in place the full
    SHA-256 digest is fed to bcrypt, so the two passwords must NOT verify
    against each other's hash.
    """
    from app.services.auth import hash_password, verify_password

    pw72 = "a" * 72
    pw73 = "a" * 72 + "b"  # same first 72 bytes, one extra byte

    hash72 = hash_password(pw72)
    hash73 = hash_password(pw73)

    # Each password must only verify against its own hash
    assert verify_password(pw72, hash72) is True
    assert verify_password(pw73, hash73) is True

    # Cross-verification must fail (this is what the truncation bug broke)
    assert verify_password(pw73, hash72) is False, (
        "73-char password verified against 72-char hash — prehash may be missing"
    )
    assert verify_password(pw72, hash73) is False


async def test_prehash_128_char_password_round_trip():
    """A 128-char password (the maximum allowed) must hash and verify correctly."""
    from app.services.auth import hash_password, verify_password

    pw128 = "x" * 128
    hashed = hash_password(pw128)
    assert verify_password(pw128, hashed) is True
    assert verify_password(pw128 + "y", hashed) is False


async def test_register_rejects_129_char_password(client):
    """Passwords longer than 128 characters must be rejected with 422."""
    pw129 = "a" * 129
    resp = await client.post(
        "/api/auth/register",
        json={"email": "toolong@b.com", "password": pw129},
    )
    assert resp.status_code == 422


# --- Legacy bcrypt migration path tests ---

async def test_legacy_bcrypt_hash_can_login_and_rehash(client):
    """A user with a legacy plain-bcrypt hash (no SHA-256 prehash) must be able
    to log in; after successful login the stored hash must be upgraded to the
    new SHA-256 prehash scheme.
    """
    import bcrypt as _bcrypt
    from app.services.auth import verify_password as new_verify

    password = "legacypassword123"

    # Build a legacy hash: raw bcrypt without SHA-256 prehash.
    legacy_hash = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=12)).decode()

    # Insert the user directly with the legacy hash.
    async with _AsyncTestSession() as session:
        user = User(email="legacy@b.com", password_hash=legacy_hash)
        session.add(user)
        await session.commit()

    # Login should succeed even though the stored hash is legacy-scheme.
    resp = await client.post(
        "/api/auth/login",
        data={"username": "legacy@b.com", "password": password},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    # After login the stored hash must have been upgraded to the new scheme.
    async with _AsyncTestSession() as session:
        from sqlalchemy import select as _select
        result = await session.execute(_select(User).where(User.email == "legacy@b.com"))
        updated_user = result.scalar_one()

    # The hash must have changed (no longer the legacy one).
    assert updated_user.password_hash != legacy_hash, (
        "Password hash was not upgraded after legacy login"
    )
    # The new hash must verify correctly with the new (SHA-256 prehash) scheme.
    assert new_verify(password, updated_user.password_hash) is True, (
        "Upgraded hash does not verify with new scheme"
    )
    # The legacy hash must NOT verify with the new scheme (different inputs).
    assert new_verify(password + "extra", updated_user.password_hash) is False


# --- JWT revocation (server-side logout) tests ---


class _InMemoryBlocklist:
    """Test double for TokenBlocklist backed by an in-memory set."""

    def __init__(self):
        self.revoked: set[str] = set()

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        if ttl_seconds > 0:
            self.revoked.add(jti)

    async def is_revoked(self, jti: str) -> bool:
        return jti in self.revoked


@pytest.fixture
def blocklist():
    """Override the blocklist dependency with one shared in-memory instance for
    the whole login -> /me -> logout -> /me sequence (mirrors get_db override)."""
    fake = _InMemoryBlocklist()
    app.dependency_overrides[get_token_blocklist] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_token_blocklist, None)


async def test_logout_revokes_token(client, blocklist):
    """After logout the same token must be rejected with 401 by /me."""
    await client.post("/api/auth/register", json={"email": "revoke@b.com", "password": "pass12345678"})
    login = await client.post("/api/auth/login", data={"username": "revoke@b.com", "password": "pass12345678"})
    cookies = login.cookies

    # Token works before logout.
    assert (await client.get("/api/auth/me", cookies=cookies)).status_code == 200

    logout = await client.post("/api/auth/logout", cookies=cookies)
    assert logout.status_code == 200
    assert len(blocklist.revoked) == 1  # exactly one jti revoked

    # Same token is now rejected server-side even though it has not expired.
    resp = await client.get("/api/auth/me", cookies=cookies)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token has been revoked"


async def test_logout_without_token_is_noop(client, blocklist):
    """Logout with no token still succeeds and revokes nothing."""
    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert blocklist.revoked == set()


async def test_non_revoked_token_still_valid(client, blocklist):
    """A token that was never logged out must keep working."""
    await client.post("/api/auth/register", json={"email": "keep@b.com", "password": "pass12345678"})
    login = await client.post("/api/auth/login", data={"username": "keep@b.com", "password": "pass12345678"})
    resp = await client.get("/api/auth/me", cookies=login.cookies)
    assert resp.status_code == 200


def test_access_token_has_unique_jti():
    """Each issued token must carry a distinct jti claim for revocation."""
    from app.services.auth import create_access_token, decode_token

    p1 = decode_token(create_access_token({"sub": "1"}))
    p2 = decode_token(create_access_token({"sub": "1"}))
    assert p1["jti"] and p2["jti"]
    assert p1["jti"] != p2["jti"]


# --- RedisTokenBlocklist unit tests (fake client, no live Redis) ---


class _FakeRedis:
    """Minimal async Redis stand-in implementing setex/exists."""

    def __init__(self):
        self.store: dict[str, str] = {}

    async def setex(self, key, ttl, value):
        self.store[key] = value

    async def exists(self, key):
        return 1 if key in self.store else 0


class _BrokenRedis:
    """Async Redis stand-in whose every call raises (simulates an outage)."""

    async def setex(self, *args, **kwargs):
        raise ConnectionError("redis down")

    async def exists(self, *args, **kwargs):
        raise ConnectionError("redis down")


async def test_redis_blocklist_revoke_and_check():
    from app.services.token_blocklist import RedisTokenBlocklist

    bl = RedisTokenBlocklist(_FakeRedis())
    assert await bl.is_revoked("abc") is False
    await bl.revoke("abc", 600)
    assert await bl.is_revoked("abc") is True


async def test_redis_blocklist_skips_nonpositive_ttl():
    """An already-expired token (ttl <= 0) is not written to the store."""
    from app.services.token_blocklist import RedisTokenBlocklist

    fake = _FakeRedis()
    bl = RedisTokenBlocklist(fake)
    await bl.revoke("expired", 0)
    await bl.revoke("expired2", -5)
    assert fake.store == {}


async def test_redis_blocklist_fails_open_on_outage():
    """Redis errors must not raise: revoke is a no-op, is_revoked returns False."""
    from app.services.token_blocklist import RedisTokenBlocklist

    bl = RedisTokenBlocklist(_BrokenRedis())
    await bl.revoke("x", 600)  # must not raise
    assert await bl.is_revoked("x") is False  # fail open


async def test_null_blocklist_never_revokes():
    from app.services.token_blocklist import NullTokenBlocklist

    bl = NullTokenBlocklist()
    await bl.revoke("x", 600)
    assert await bl.is_revoked("x") is False
