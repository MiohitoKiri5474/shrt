# Runbook

Operational reference for running Shrt in production. For env var reference and Compose topology, see [SETUP.md](SETUP.md). For endpoint shapes, see [API.md](API.md).

There is no CD pipeline in this repo (`.github/workflows/` only runs tests and a dependency audit) — deploys are manual `docker compose` on the target host.

## Deployment

```bash
# On the target host, first time:
git clone <repo> && cd shrt
cp .env.example .env            # fill in SECRET_KEY, DATABASE_URL, REDIS_PASSWORD, CORS_ALLOWED_ORIGINS, etc. — see SETUP.md
cp redis/redis.conf.example redis/redis.conf   # set requirepass to match REDIS_PASSWORD in .env
mkdir -p ./backend-data && chown 10001:10001 ./backend-data   # backend container runs as uid 10001

docker compose up --build -d
```

```bash
# Subsequent deploys:
git pull
docker compose up --build -d
```

Compose brings up `redis` → `backend` (waits for redis healthy) → `frontend` (waits for backend healthy), per the `depends_on: condition: service_healthy` chain in `docker-compose.yml`.

## Health checks

| Check | Command / URL | Expected |
|---|---|---|
| Backend liveness | `GET http://localhost:8000/health` (internal) or `GET /api/health` through nginx | `{"status": "ok"}`, 200 |
| Redis | `docker compose exec redis redis-cli --no-auth-warning -a "$REDIS_PASSWORD" ping` | `PONG` |
| Container health status | `docker compose ps` | all services `healthy` |
| Frontend serving | `curl -I http://localhost/` (or `$HOST_PORT`) | 200 |

`docker-compose.yml` healthchecks: redis every 15s, backend every 30s. `frontend` has no explicit healthcheck (nginx failing to start fails the container itself).

## Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `Container shrt-backend Error dependency backend failed to start` | `./backend-data` not writable by uid `10001`, or `SECRET_KEY`/`DATABASE_URL` unset | `mkdir -p ./backend-data && chown 10001:10001 ./backend-data`; check `docker compose logs backend` for the specific `KeyError`/`ValueError` from `config.py` |
| Backend refuses to start with a `ValueError` about `DATABASE_URL` | SQLite URL used with `APP_ENV` not in `development`/`dev`/`test`/`testing` | Switch to a PostgreSQL `DATABASE_URL`, or set `APP_ENV=development` for non-production use only |
| Backend refuses to start, weak-password `RuntimeError` | `DEFAULT_USER_PASSWORD` is on the known weak-password list in production | Set a stronger seed password in `.env` |
| Redis container unhealthy / backend can't reach Redis | `REDIS_PASSWORD` in `.env` doesn't match `requirepass` in `redis/redis.conf` | Keep the two in sync by hand (Redis reads its password from the mounted config, not `REDIS_URL`) |
| Rate limits trip on every request from behind a proxy/CDN | `TRUSTED_PROXY_CIDRS` unset — all requests share one bucket, or `X-Forwarded-For` isn't trusted | Set `TRUSTED_PROXY_CIDRS` to the Docker bridge subnet (`docker network inspect <project>_app-net --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'`) |
| Reloading a client-side route (e.g. `/manage`) returns a raw JSON error instead of the app | A short code or a new frontend route collides with the nginx SPA-fallback regex | Any new top-level frontend route must be added to both `frontend/src/router/index.ts` and the regex in `frontend/nginx.conf`, and to `RESERVED_SHORT_CODES` in `backend/src/app/schemas.py` |
| SQLite data lost after `docker compose down -v` | N/A — `backend-data` is a bind mount, not a named volume, so `-v` does not remove it | If data is actually missing, check `./backend-data/shortener.db` exists on the host and the mount path matches `docker-compose.yml` |

## Rollback

No image registry/tagging is set up — "rollback" means reverting the checked-out commit and rebuilding:

```bash
git log --oneline -10          # find the last known-good commit
git checkout <commit-or-tag>
docker compose up --build -d
```

Database migrations in this project are additive-only (`database.py::_migrate_schema()`, no Alembic, no down-migrations) — rolling back code does not undo schema changes. If a bad deploy added columns, a git rollback leaves them in place (harmless, since older code just doesn't read them) rather than reverting them automatically.

## Backups

SQLite (dev/single-host use): back up `./backend-data/shortener.db` (file copy while the backend is stopped, or use `sqlite3 .backup`).

PostgreSQL (production): use your standard `pg_dump`/managed-backup process — this repo does not include one.

## Alerting / escalation

Not configured in this repo. `docker compose ps` / the healthchecks above are the only built-in signals. If you wire up external monitoring, point it at `GET /api/health` (rate-limited at 60/min, safe for a ~30s poll interval per the comment in `main.py`).
