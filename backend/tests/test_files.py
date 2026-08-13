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


async def test_upload_txt_with_null_byte_rejected(auth_client):
    """.txt/.csv have no magic-byte signature to sniff, but a null byte is
    never valid text content — binary data renamed to .txt must be rejected."""
    resp = await auth_client.post(
        "/api/files",
        data={"kind": "file"},
        files={"file": ("notes.txt", b"binary\x00data", "text/plain")},
    )
    assert resp.status_code == 422


async def test_upload_plain_txt_accepted(auth_client):
    resp = await auth_client.post(
        "/api/files",
        data={"kind": "file"},
        files={"file": ("notes.txt", b"just plain text, no null bytes here", "text/plain")},
    )
    assert resp.status_code == 201


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
    assert resp.headers["x-content-type-options"] == "nosniff"


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


async def test_upload_with_password_sets_has_password_true(auth_client):
    resp = await auth_client.post(
        "/api/files",
        data={"kind": "file", "password": "secretpw"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["has_password"] is True


async def test_upload_without_password_has_password_false(auth_client):
    resp = await auth_client.post(
        "/api/files",
        data={"kind": "file"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["has_password"] is False


async def test_upload_password_too_short_rejected(auth_client):
    resp = await auth_client.post(
        "/api/files",
        data={"kind": "file", "password": "short"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    assert resp.status_code == 422


async def test_unlock_file_correct_password_returns_download_url_with_token(auth_client):
    create = await auth_client.post(
        "/api/files",
        data={"kind": "file", "password": "secretpw"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    code = create.json()["short_code"]
    resp = await auth_client.post(f"/api/files/{code}/unlock", json={"password": "secretpw"})
    assert resp.status_code == 200
    download_url = resp.json()["download_url"]
    assert download_url.startswith(f"/f/{code}?token=")
    assert len(download_url.split("token=")[1]) > 0


async def test_unlock_file_wrong_password_401(auth_client):
    create = await auth_client.post(
        "/api/files",
        data={"kind": "file", "password": "secretpw"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    code = create.json()["short_code"]
    resp = await auth_client.post(f"/api/files/{code}/unlock", json={"password": "wrongpw1"})
    assert resp.status_code == 401


async def test_unlock_file_not_password_protected_400(auth_client):
    create = await auth_client.post(
        "/api/files",
        data={"kind": "file"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    code = create.json()["short_code"]
    resp = await auth_client.post(f"/api/files/{code}/unlock", json={"password": "whatever1"})
    assert resp.status_code == 400


async def test_unlock_file_not_found_404(client):
    resp = await client.post("/api/files/notfound8/unlock", json={"password": "whatever1"})
    assert resp.status_code == 404


async def test_unlock_expired_file_410(auth_client):
    from app.database import get_db as _get_db
    create = await auth_client.post(
        "/api/files",
        data={"kind": "file", "password": "secretpw"},
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
    resp = await auth_client.post(f"/api/files/{code}/unlock", json={"password": "secretpw"})
    assert resp.status_code == 410


async def test_serve_password_protected_file_without_token_redirects_to_gate(auth_client):
    """A visitor opening a password-protected /f/:code link cold (no token,
    e.g. pasted from a message) must land on the same password gate links
    use, not a bare JSON 401 with nothing to enter a password into."""
    create = await auth_client.post(
        "/api/files",
        data={"kind": "file", "password": "secretpw"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    code = create.json()["short_code"]
    resp = await auth_client.get(f"/f/{code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == f"/p/{code}?type=file"


async def test_serve_password_protected_image_without_token_redirects_to_gate(auth_client):
    create = await auth_client.post(
        "/api/files",
        data={"kind": "image", "password": "secretpw"},
        files={"file": ("pic.png", PNG_BYTES, "image/png")},
    )
    code = create.json()["short_code"]
    resp = await auth_client.get(f"/f/{code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == f"/p/{code}?type=file"


async def test_serve_password_protected_file_with_valid_token_succeeds(auth_client):
    create = await auth_client.post(
        "/api/files",
        data={"kind": "file", "password": "secretpw"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    code = create.json()["short_code"]
    unlock = await auth_client.post(f"/api/files/{code}/unlock", json={"password": "secretpw"})
    download_url = unlock.json()["download_url"]
    resp = await auth_client.get(download_url)
    assert resp.status_code == 200
    assert resp.content == PDF_BYTES


async def test_serve_password_protected_file_with_garbage_token_401(auth_client):
    create = await auth_client.post(
        "/api/files",
        data={"kind": "file", "password": "secretpw"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    code = create.json()["short_code"]
    resp = await auth_client.get(f"/f/{code}?token=not-a-real-token")
    assert resp.status_code == 401


async def test_serve_password_protected_file_with_token_for_different_file_401(auth_client):
    create_a = await auth_client.post(
        "/api/files",
        data={"kind": "file", "password": "secretpw"},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    code_a = create_a.json()["short_code"]
    create_b = await auth_client.post(
        "/api/files",
        data={"kind": "file", "password": "otherpw1"},
        files={"file": ("other.pdf", PDF_BYTES, "application/pdf")},
    )
    code_b = create_b.json()["short_code"]
    unlock_a = await auth_client.post(f"/api/files/{code_a}/unlock", json={"password": "secretpw"})
    token_a = unlock_a.json()["download_url"].split("token=")[1]
    resp = await auth_client.get(f"/f/{code_b}?token={token_a}")
    assert resp.status_code == 401
