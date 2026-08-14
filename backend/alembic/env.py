import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# disable_existing_loggers=False: run_migrations() (app.database) runs this
# in-process on every boot, not just via the standalone `alembic` CLI — the
# default True would disable every already-registered logger (uvicorn's
# included) that isn't named in this ini's [loggers] section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

from app.config import DATABASE_URL
from app.models import Base

target_metadata = Base.metadata

# Reuse the same DATABASE_URL the running app uses, rather than a second
# copy of it living in alembic.ini. config.attributes carries a per-invocation
# override for tests exercising a scratch database (see app.database.run_migrations).
# `%` is escaped either way because Config wraps a ConfigParser with
# interpolation enabled — a literal `%` (e.g. a percent-encoded character in
# a password) would otherwise raise ValueError the next time this is read.
_raw_url = config.attributes.get("sqlalchemy_url_override", DATABASE_URL)
config.set_main_option("sqlalchemy.url", _raw_url.replace("%", "%%"))

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # SQLite can't ALTER most column definitions outside of batch mode; this
    # baseline is create-only so it doesn't need it yet, but the next
    # migration that alters a column against the SQLite dev/test dialect will.
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
