import pytest
from unittest.mock import patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models import Base, User
from app.main import seed_default_user


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def test_seed_creates_user(session_factory, monkeypatch):
    monkeypatch.setenv("DEFAULT_USER_EMAIL", "seed@test.com")
    monkeypatch.setenv("DEFAULT_USER_PASSWORD", "testpass")
    with patch("app.main.AsyncSessionLocal", session_factory):
        await seed_default_user()
    async with session_factory() as db:
        result = await db.execute(select(User).where(User.email == "seed@test.com"))
        assert result.scalar_one_or_none() is not None


async def test_seed_idempotent(session_factory, monkeypatch):
    monkeypatch.setenv("DEFAULT_USER_EMAIL", "seed@test.com")
    monkeypatch.setenv("DEFAULT_USER_PASSWORD", "testpass")
    with patch("app.main.AsyncSessionLocal", session_factory):
        await seed_default_user()
        await seed_default_user()
    async with session_factory() as db:
        result = await db.execute(select(User).where(User.email == "seed@test.com"))
        assert len(result.scalars().all()) == 1


async def test_seed_skips_without_env(session_factory, monkeypatch):
    monkeypatch.delenv("DEFAULT_USER_EMAIL", raising=False)
    monkeypatch.delenv("DEFAULT_USER_PASSWORD", raising=False)
    with patch("app.main.AsyncSessionLocal", session_factory):
        await seed_default_user()
    async with session_factory() as db:
        result = await db.execute(select(User))
        assert result.scalars().all() == []
