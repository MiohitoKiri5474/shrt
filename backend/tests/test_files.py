import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy import update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Base, SharedFile

PDF_BYTES = b"%PDF-1.4\n%mock pdf content for tests\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
FAKE_EXE_BYTES = b"MZ\x90\x00" + b"\x00" * 32


@pytest.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORAGE_DIR", str(tmp_path / "files"))
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


async def test_upload_file_success(auth_client):
    resp = await auth_client.post(
        "/api/files",
        data={"kind": "file"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["kind"] == "file"
    assert data["original_filename"] == "report.pdf"
    assert data["mime_type"] == "application/pdf"
    assert len(data["short_code"]) == 8
    assert data["expires_at"] is not None


async def test_upload_image_no_expiry(auth_client):
    resp = await auth_client.post(
        "/api/files",
        data={"kind": "image"},
        files={"file": ("pic.png", PNG_BYTES, "image/png")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["kind"] == "image"
    assert data["expires_at"] is None


async def test_upload_disallowed_extension_rejected(auth_client):
    resp = await auth_client.post(
        "/api/files",
        data={"kind": "file"},
        files={"file": ("virus.exe", FAKE_EXE_BYTES, "application/octet-stream")},
    )
    assert resp.status_code == 422


async def test_upload_content_mismatch_rejected(auth_client):
    """A .pdf extension whose bytes don't match the PDF magic number must be
    rejected — extension alone is not proof of content type."""
    resp = await auth_client.post(
        "/api/files",
        data={"kind": "file"},
        files={"file": ("fake.pdf", FAKE_EXE_BYTES, "application/pdf")},
    )
    assert resp.status_code == 422


async def test_upload_image_extension_rejected_for_file_kind(auth_client):
    resp = await auth_client.post(
        "/api/files",
        data={"kind": "file"},
        files={"file": ("pic.png", PNG_BYTES, "image/png")},
    )
    assert resp.status_code == 422


async def test_upload_too_large_rejected(auth_client):
    oversized = PDF_BYTES + b"\x00" * (25 * 1024 * 1024)
    resp = await auth_client.post(
        "/api/files",
        data={"kind": "file"},
        files={"file": ("big.pdf", oversized, "application/pdf")},
    )
    assert resp.status_code == 413


async def test_image_quota_exceeded_rejected(auth_client, monkeypatch):
    monkeypatch.setattr("app.routers.files.IMAGE_QUOTA_BYTES", 10)
    resp = await auth_client.post(
        "/api/files",
        data={"kind": "image"},
        files={"file": ("pic.png", PNG_BYTES, "image/png")},
    )
    assert resp.status_code == 413


async def test_download_file_forces_attachment(auth_client):
    create = await auth_client.post(
        "/api/files",
        data={"kind": "file"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    code = create.json()["short_code"]
    resp = await auth_client.get(f"/f/{code}")
    assert resp.status_code == 200
    assert resp.content == PDF_BYTES
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]


async def test_serve_image_inline(auth_client):
    create = await auth_client.post(
        "/api/files",
        data={"kind": "image"},
        files={"file": ("pic.png", PNG_BYTES, "image/png")},
    )
    code = create.json()["short_code"]
    resp = await auth_client.get(f"/f/{code}")
    assert resp.status_code == 200
    assert resp.content == PNG_BYTES
    assert "inline" in resp.headers["content-disposition"]


async def test_serve_not_found(client):
    resp = await client.get("/f/notfound8")
    assert resp.status_code == 404


async def test_serve_expired_file_404(auth_client):
    from app.database import get_db as _get_db
    create = await auth_client.post(
        "/api/files",
        data={"kind": "file"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    code = create.json()["short_code"]
    override = app.dependency_overrides[_get_db]
    async for db in override():
        await db.execute(
            update(SharedFile)
            .where(SharedFile.short_code == code)
            .values(expires_at=datetime.now(timezone.utc) - timedelta(days=1))
        )
        await db.commit()
        break
    resp = await auth_client.get(f"/f/{code}")
    assert resp.status_code == 404


async def test_list_files(auth_client):
    await auth_client.post(
        "/api/files", data={"kind": "file"}, files={"file": ("a.pdf", PDF_BYTES, "application/pdf")}
    )
    await auth_client.post(
        "/api/files", data={"kind": "image"}, files={"file": ("b.png", PNG_BYTES, "image/png")}
    )
    resp = await auth_client.get("/api/files")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_delete_file(auth_client):
    create = await auth_client.post(
        "/api/files", data={"kind": "file"}, files={"file": ("a.pdf", PDF_BYTES, "application/pdf")}
    )
    file_id = create.json()["id"]
    resp = await auth_client.delete(f"/api/files/{file_id}")
    assert resp.status_code == 204
    resp = await auth_client.get("/api/files")
    assert resp.json() == []


async def test_delete_file_not_owner(client, auth_client):
    create = await auth_client.post(
        "/api/files", data={"kind": "file"}, files={"file": ("a.pdf", PDF_BYTES, "application/pdf")}
    )
    file_id = create.json()["id"]
    await client.post("/api/auth/register", json={"email": "other@b.com", "password": "pass12345678"})
    await client.post("/api/auth/login", data={"username": "other@b.com", "password": "pass12345678"})
    resp = await client.delete(f"/api/files/{file_id}")
    assert resp.status_code == 404


async def test_delete_file_not_found(auth_client):
    resp = await auth_client.delete("/api/files/99999")
    assert resp.status_code == 404


async def test_upload_requires_auth(client):
    resp = await client.post(
        "/api/files", data={"kind": "file"}, files={"file": ("a.pdf", PDF_BYTES, "application/pdf")}
    )
    assert resp.status_code == 401
