import os
import tempfile

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.database import run_migrations
from app.models import Base


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # aiosqlite creates the file itself; only the path is needed
    yield path
    if os.path.exists(path):
        os.remove(path)


def _database_url(path: str) -> str:
    return f"sqlite+aiosqlite:///{path}"


async def _table_columns(path: str) -> dict[str, set[str]]:
    engine = create_async_engine(_database_url(path))
    try:
        async with engine.connect() as conn:
            def inspect_columns(sync_conn):
                insp = inspect(sync_conn)
                return {
                    table: {col["name"] for col in insp.get_columns(table)}
                    for table in insp.get_table_names()
                }
            return await conn.run_sync(inspect_columns)
    finally:
        await engine.dispose()


async def test_fresh_database_creates_all_tables(db_path):
    await run_migrations(database_url=_database_url(db_path))

    columns = await _table_columns(db_path)
    assert "alembic_version" in columns
    for table_name, table in Base.metadata.tables.items():
        expected = {c.name for c in table.columns}
        assert columns[table_name] == expected


async def test_running_twice_is_idempotent(db_path):
    await run_migrations(database_url=_database_url(db_path))
    first = await _table_columns(db_path)

    await run_migrations(database_url=_database_url(db_path))
    second = await _table_columns(db_path)

    assert first == second


async def test_legacy_database_gets_stamped_instead_of_recreated(db_path):
    # Simulate a database left over from before Alembic: the current schema
    # exists (created directly via Base.metadata, as the old create_tables()
    # used to), but there's no alembic_version table yet.
    engine = create_async_engine(_database_url(db_path))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    before = await _table_columns(db_path)
    assert "alembic_version" not in before

    await run_migrations(database_url=_database_url(db_path))

    after = await _table_columns(db_path)
    assert "alembic_version" in after
    for table_name, table in Base.metadata.tables.items():
        expected = {c.name for c in table.columns}
        assert after[table_name] == expected

    # A second run on the now-stamped database is a no-op, not an error.
    await run_migrations(database_url=_database_url(db_path))
    assert await _table_columns(db_path) == after
