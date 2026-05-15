from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL
from app.models import Base

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables():  # pragma: no cover
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():  # pragma: no cover
    async with AsyncSessionLocal() as session:
        yield session
