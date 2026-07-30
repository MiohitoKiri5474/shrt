import asyncio
import os
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

_is_sqlite = DATABASE_URL.startswith("sqlite")
_pool_kwargs = (
    {}
    if _is_sqlite
    else {
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
        "pool_pre_ping": True,
    }
)
engine = create_async_engine(DATABASE_URL, echo=False, **_pool_kwargs)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _alembic_config(database_url: str | None) -> AlembicConfig:
    cfg = AlembicConfig(str(_ALEMBIC_INI))
    if database_url is not None:
        cfg.attributes["sqlalchemy_url_override"] = database_url
    return cfg


def _upgrade_head(database_url: str | None) -> None:
    alembic_command.upgrade(_alembic_config(database_url), "head")


def _stamp_head(database_url: str | None) -> None:
    alembic_command.stamp(_alembic_config(database_url), "head")


async def run_migrations(database_url: str | None = None) -> None:
    """Bring the schema up to date via Alembic, run automatically at boot.

    A database from before Alembic was adopted has the current tables but no
    `alembic_version` row — stamping it to head first (no DDL) tells Alembic
    it's already caught up, since every past schema change ran automatically
    on every boot and there's a single deployment target, not a fleet of
    independently-drifted databases. A fresh database and one already tracked
    by Alembic both just upgrade normally.

    `database_url` overrides the app's own `engine`/`DATABASE_URL` — used by
    tests to exercise this function against a scratch database, since the
    running app always calls this with no argument.
    """
    target_engine = engine if database_url is None else create_async_engine(database_url)
    try:
        async with target_engine.connect() as conn:
            tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))

        loop = asyncio.get_running_loop()
        if "alembic_version" not in tables and "users" in tables:
            await loop.run_in_executor(None, _stamp_head, database_url)
        await loop.run_in_executor(None, _upgrade_head, database_url)
    finally:
        if database_url is not None:
            await target_engine.dispose()


async def get_db():  # pragma: no cover
    async with AsyncSessionLocal() as session:
        yield session
