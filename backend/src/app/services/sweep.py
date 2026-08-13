import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SharedFile
from app.services.uploads import delete_blob

logger = logging.getLogger(__name__)

SWEEP_INTERVAL_SECONDS = 15 * 60


async def sweep_expired_files(db: AsyncSession) -> int:
    """Delete every kind='file' row past its expires_at, plus its on-disk blob.

    Rows with expires_at IS NULL (images) and not-yet-expired files are left
    untouched. Returns the number of rows deleted.
    """
    # expires_at is a naive DateTime column (no timezone=True) storing UTC —
    # asyncpg rejects a tz-aware datetime bound against a TIMESTAMP WITHOUT
    # TIME ZONE column, so strip tzinfo before using it as a query parameter.
    # SQLite silently accepted the tz-aware form, which is why this only
    # surfaces against Postgres.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await db.execute(
        select(SharedFile).where(SharedFile.kind == "file", SharedFile.expires_at <= now)
    )
    expired = list(result.scalars())
    for shared_file in expired:
        delete_blob(shared_file.storage_path)
        await db.delete(shared_file)
    await db.commit()
    return len(expired)


async def run_sweep_loop(session_factory: Callable[[], AsyncSession]) -> None:  # pragma: no cover
    """Run sweep_expired_files on a fixed interval until cancelled.

    Intended to be started as an asyncio.create_task() in the app's lifespan
    and cancelled on shutdown. session_factory is a callable returning an
    async context manager yielding an AsyncSession (e.g. AsyncSessionLocal).
    """
    while True:
        try:
            async with session_factory() as db:
                deleted = await sweep_expired_files(db)
                if deleted:
                    logger.info("Swept %d expired file(s)", deleted)
        except Exception:
            logger.exception("File sweep iteration failed")
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
