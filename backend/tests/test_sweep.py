from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, SharedFile, User
from app.services.sweep import sweep_expired_files


@pytest.fixture
async def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORAGE_DIR", str(tmp_path / "files"))
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    AsyncTestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncTestSession() as session:
        yield session
    await engine.dispose()


async def _make_user(db: AsyncSession) -> User:
    user = User(email="owner@b.com", password_hash="hash")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _write_blob(tmp_path, short_code: str) -> str:
    files_dir = tmp_path / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    blob_path = files_dir / short_code
    blob_path.write_bytes(b"content")
    return str(blob_path)


async def test_sweep_deletes_expired_file_row_and_blob(db_session, tmp_path):
    user = await _make_user(db_session)
    storage_path = _write_blob(tmp_path, "expired1")
    expired = SharedFile(
        user_id=user.id,
        short_code="expired1",
        kind="file",
        original_filename="a.pdf",
        mime_type="application/pdf",
        size_bytes=7,
        storage_path=storage_path,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(expired)
    await db_session.commit()

    count = await sweep_expired_files(db_session)

    assert count == 1
    result = await db_session.execute(select(SharedFile).where(SharedFile.short_code == "expired1"))
    assert result.scalar_one_or_none() is None
    assert not Path(storage_path).exists()


async def test_sweep_leaves_not_yet_expired_file_untouched(db_session, tmp_path):
    user = await _make_user(db_session)
    storage_path = _write_blob(tmp_path, "future1")
    future = SharedFile(
        user_id=user.id,
        short_code="future1",
        kind="file",
        original_filename="b.pdf",
        mime_type="application/pdf",
        size_bytes=7,
        storage_path=storage_path,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db_session.add(future)
    await db_session.commit()

    count = await sweep_expired_files(db_session)

    assert count == 0
    result = await db_session.execute(select(SharedFile).where(SharedFile.short_code == "future1"))
    assert result.scalar_one_or_none() is not None
    assert Path(storage_path).exists()


async def test_sweep_leaves_images_untouched(db_session, tmp_path):
    user = await _make_user(db_session)
    storage_path = _write_blob(tmp_path, "image1")
    image = SharedFile(
        user_id=user.id,
        short_code="image1",
        kind="image",
        original_filename="pic.png",
        mime_type="image/png",
        size_bytes=7,
        storage_path=storage_path,
        expires_at=None,
    )
    db_session.add(image)
    await db_session.commit()

    count = await sweep_expired_files(db_session)

    assert count == 0
    result = await db_session.execute(select(SharedFile).where(SharedFile.short_code == "image1"))
    assert result.scalar_one_or_none() is not None
    assert Path(storage_path).exists()


async def test_sweep_returns_count_and_mixed_rows(db_session, tmp_path):
    user = await _make_user(db_session)
    now = datetime.now(timezone.utc)

    expired_paths = []
    for i in range(2):
        code = f"exp{i}"
        storage_path = _write_blob(tmp_path, code)
        expired_paths.append(storage_path)
        db_session.add(
            SharedFile(
                user_id=user.id,
                short_code=code,
                kind="file",
                original_filename=f"{code}.pdf",
                mime_type="application/pdf",
                size_bytes=7,
                storage_path=storage_path,
                expires_at=now - timedelta(seconds=1),
            )
        )

    future_storage = _write_blob(tmp_path, "future2")
    db_session.add(
        SharedFile(
            user_id=user.id,
            short_code="future2",
            kind="file",
            original_filename="future.pdf",
            mime_type="application/pdf",
            size_bytes=7,
            storage_path=future_storage,
            expires_at=now + timedelta(days=1),
        )
    )

    image_storage = _write_blob(tmp_path, "img2")
    db_session.add(
        SharedFile(
            user_id=user.id,
            short_code="img2",
            kind="image",
            original_filename="img.png",
            mime_type="image/png",
            size_bytes=7,
            storage_path=image_storage,
            expires_at=None,
        )
    )
    await db_session.commit()

    count = await sweep_expired_files(db_session)

    assert count == 2
    for path in expired_paths:
        assert not Path(path).exists()
    assert Path(future_storage).exists()
    assert Path(image_storage).exists()

    result = await db_session.execute(select(SharedFile))
    remaining_codes = {row.short_code for row in result.scalars()}
    assert remaining_codes == {"future2", "img2"}


async def test_sweep_no_expired_rows_returns_zero(db_session):
    count = await sweep_expired_files(db_session)
    assert count == 0
