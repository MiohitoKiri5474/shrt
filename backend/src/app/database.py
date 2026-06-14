from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL
from app.models import Base

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables():  # pragma: no cover
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_schema(conn)


async def _migrate_schema(conn) -> None:  # pragma: no cover
    if engine.dialect.name == "sqlite":
        result = await conn.execute(text("PRAGMA table_info(users)"))
        existing = {row[1] for row in result.fetchall()}
        if "is_admin" not in existing:
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
            )
        if "username" not in existing:
            await conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(50)"))
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username "
                    "ON users (username) WHERE username IS NOT NULL"
                )
            )

        # Migrate original_url column from TEXT to VARCHAR(2048) if needed
        result = await conn.execute(text("PRAGMA table_info(urls)"))
        urls_columns = {row[1]: row[2] for row in result.fetchall()}
        if urls_columns.get("original_url", "").upper() == "TEXT":
            try:
                await conn.execute(
                    text("ALTER TABLE urls RENAME COLUMN original_url TO original_url_old")
                )
                await conn.execute(
                    text("ALTER TABLE urls ADD COLUMN original_url VARCHAR(2048)")
                )
                await conn.execute(
                    text("UPDATE urls SET original_url = SUBSTR(original_url_old, 1, 2048)")
                )
                await conn.execute(text("ALTER TABLE urls DROP COLUMN original_url_old"))
            except Exception:
                pass  # column already migrated or different DB
    else:
        result = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'is_admin' "
                "AND table_schema = 'public'"
            )
        )
        if not result.fetchone():
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE")
            )
        result = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'username' "
                "AND table_schema = 'public'"
            )
        )
        if not result.fetchone():
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN username VARCHAR(50) UNIQUE")
            )

        # Migrate original_url column from TEXT to VARCHAR(2048) if needed
        result = await conn.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'urls' AND column_name = 'original_url' "
                "AND table_schema = 'public'"
            )
        )
        row = result.fetchone()
        if row and row[0].upper() == "TEXT":
            await conn.execute(
                text(
                    "ALTER TABLE urls ALTER COLUMN original_url TYPE VARCHAR(2048) "
                    "USING SUBSTR(original_url, 1, 2048)"
                )
            )


async def get_db():  # pragma: no cover
    async with AsyncSessionLocal() as session:
        yield session
