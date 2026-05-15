import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, URL, Click

@pytest.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s

async def test_user_model(session):
    user = User(email="test@example.com", password_hash="hashed")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    assert user.id is not None
    assert user.email == "test@example.com"

async def test_url_model(session):
    user = User(email="u@example.com", password_hash="h")
    session.add(user)
    await session.commit()
    url = URL(user_id=user.id, original_url="https://example.com", short_code="abc12345")
    session.add(url)
    await session.commit()
    await session.refresh(url)
    assert url.id is not None
    assert url.short_code == "abc12345"

async def test_click_model(session):
    user = User(email="c@example.com", password_hash="h")
    session.add(user)
    await session.commit()
    url = URL(user_id=user.id, original_url="https://example.com", short_code="xxxxxxxx")
    session.add(url)
    await session.commit()
    click = Click(url_id=url.id, ip_address="127.0.0.1", user_agent="test-agent")
    session.add(click)
    await session.commit()
    await session.refresh(click)
    assert click.id is not None
