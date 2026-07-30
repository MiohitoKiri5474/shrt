# Adopt Alembic for schema migrations

Schema changes were hand-rolled in `database.py::_migrate_schema()` as dialect-specific, idempotent `ALTER` statements re-checked on every boot — four accumulated so far (`is_admin`/`username`, widening `original_url`, `password_hash`, `expires_at`), with no rollback path and growing SQLite/Postgres branching. We're adopting Alembic with a **single baseline revision** capturing the current schema as-is (existing databases get `alembic stamp head`) rather than reconstructing each historical additive change — nothing depends on rolling back through states nobody will revisit. `alembic upgrade head` runs programmatically inside `lifespan()` before the app serves requests, preserving the existing single-command Docker Compose boot (no new ops step), across both SQLite (dev/test) and Postgres (prod).

## Consequences

Concurrent multi-replica boot would race on `alembic upgrade head`. Not an issue today (single backend service, no replicas configured) — needs a lock/guard if the backend is ever scaled horizontally.
