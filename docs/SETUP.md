# Setup & Deployment

For the minimal quick-start, see the root [README.md](../README.md). This doc covers every environment variable and the Docker Compose topology in full.

## Environment variables

Copy `.env.example` to `.env` before starting. All are read by `backend/src/app/config.py` / `main.py` / `rate_limiter.py` unless noted.

Also copy `redis/redis.conf.example` to `redis/redis.conf` and set its `requirepass` to the **same** value as `REDIS_PASSWORD` below — Redis reads its password from that mounted config file (not a command-line flag), so the two must be kept in sync by hand. See the comments in `redis/redis.conf.example` for details.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `SECRET_KEY` | Yes | — (`KeyError` if unset) | JWT signing secret, HS256. Must be ≥64 chars. Generate: `python3 -c "import secrets; print(secrets.token_hex(48))"` |
| `DATABASE_URL` | Yes | — (`KeyError` if unset) | SQLAlchemy async connection string. `sqlite+aiosqlite:///...` only allowed when `APP_ENV` is `development`/`dev`/`test`/`testing`; any other env requires PostgreSQL (`postgresql+asyncpg://...`) or startup raises `ValueError`. |
| `REDIS_PASSWORD` | Yes | — | Must match `requirepass` in `redis/redis.conf` (see above). Used by `docker-compose.yml` to build `REDIS_URL` for the backend and as `REDISCLI_AUTH` for the redis container's healthcheck. Must not contain `changeme` outside dev (startup raises). Generate: `openssl rand -hex 32`. |
| `APP_ENV` | No | `production` | `development`/`dev` relaxes: disables `Secure` cookie flag, enables `/docs`/`/redoc`/`/openapi.json`, allows SQLite. |
| `DEFAULT_USER_EMAIL` / `DEFAULT_USER_PASSWORD` | No (seeding skipped if either unset) | — | Seeds an admin user (`is_admin=True`) on startup if no user with that email exists. Password must pass `UserCreate` validation (12-128 chars) and must not be one of a known weak-password list — in production, a weak password raises `RuntimeError` and the app refuses to start. |
| `DEFAULT_USER_USERNAME` | No | — | Optional username for the seeded admin (email always works for login regardless). |
| `ALLOW_REGISTRATION` | No | disabled | Gates `POST /api/auth/register`. Set to `true`/`1`/`yes`/`on` to allow public self-registration; otherwise it returns `403`. Does not affect admin-created users via `POST /api/auth/users`. |
| `CORS_ALLOWED_ORIGINS` | Yes in production | `http://localhost:5173,http://localhost:80` (dev only) | Comma-separated allowed origins. Startup raises if unset outside development. |
| `ALLOWED_HOSTS` | No | derived from `CORS_ALLOWED_ORIGINS` in production; `*` in dev | Comma-separated hostnames accepted in the `Host` header (`TrustedHostMiddleware`). Prevents Host-header injection into the QR-code short link (`GET /api/urls/{code}/qr` builds it from `request.base_url`). Set explicitly when the backend is reachable under a different host than the frontend origins; startup raises in production if no hosts can be derived and this is unset. |
| `TRUSTED_PROXY_CIDRS` | No | empty | Comma-separated CIDRs whose direct connections are trusted to set `X-Forwarded-For` for rate-limit IP resolution (e.g. the Docker bridge subnet nginx runs on). Empty means all requests share one rate-limit bucket — a startup warning is logged. Find your subnet: `docker network inspect <project>_app-net --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'` |
| `TRUSTED_PROXY_IPS` | No | empty | Comma-separated individual trusted proxy IPs, for proxies that don't fit a CIDR (e.g. a fixed LB VIP). Combined with `TRUSTED_PROXY_CIDRS`. |
| `HOST_PORT` | No | `80` | Host-side port the `frontend` container's port 80 is published on (`docker-compose.yml`). |

`REDIS_URL` itself is **not** set by hand — `docker-compose.yml` derives it as `redis://:${REDIS_PASSWORD}@redis:6379` and injects it into the backend container. If `REDIS_URL` is unset (e.g. running the backend outside Compose), rate limiting falls back to an in-memory store with a startup warning — not safe for multi-worker/production use.

### Frontend build-time variable

Set in `frontend/.env` (dev) or `frontend/.env.production` (prod build), not the root `.env`:

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | API origin baked into the build. Empty/same-origin works when nginx proxies `/api/*` to the backend on the same host. Set to an absolute HTTPS URL for split-host deployments. |

## Docker Compose topology

`docker-compose.yml` (production) defines three services on a single bridge network (`app-net`):

| Service | Image/Build | Exposed | Depends on | Healthcheck |
|---|---|---|---|---|
| `redis` | `redis:7-alpine`, runs as uid `999:1000` | internal `6379` only | — | `redis-cli ping` (auth via `REDISCLI_AUTH` env var), 15s interval |
| `backend` | builds `./backend` | internal `8000` only | `redis` (healthy) | `GET /health` via `urllib`, 30s interval |
| `frontend` | builds `./frontend`, runs as uid `101:101` | `${HOST_PORT:-80}:80` | `backend` (healthy) | none |

All three set `security_opt: no-new-privileges:true`, `cap_drop: ALL`, and `read_only: true` (with targeted `tmpfs` mounts for the paths each service needs to write); `frontend` additionally adds back `NET_BIND_SERVICE` to bind port 80 as non-root. Redis persistence is intentionally disabled (`save ""` / `appendonly no` in `redis/redis.conf`) — rate-limit counters don't need to survive a restart, and all backend workers share the one Redis instance for consistent limits.

Backend data (SQLite file, if used) lives in the host bind mount `./backend-data`, mounted at `/app/data`. `docker compose down -v` does not remove bind mounts, unlike named volumes. On Linux hosts, the directory must be writable by uid `10001` (the container's `appuser`): `mkdir -p ./backend-data && chown 10001:10001 ./backend-data`.

`docker-compose.dev.yml` is an override, not a default — pass it explicitly:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

It switches the backend command to `uvicorn ... --reload`, sets `APP_ENV=development`, and bind-mounts `./backend/src` into the container for hot reload.

## Database migrations

There is no Alembic. `database.py::create_tables()` runs `Base.metadata.create_all()` then `_migrate_schema()`, which hand-rolls additive migrations (adding `is_admin`/`username`/`password_hash`/`expires_at` columns, widening `original_url` to `VARCHAR(2048)`) with separate code paths for SQLite (`PRAGMA table_info`) and PostgreSQL (`information_schema.columns`). New schema changes need a corresponding block added there.

## Nginx (frontend container)

`frontend/nginx.conf`:
- Rate-limits `/api/*` at the edge: 30 req/min per IP (`limit_req_zone`, burst 10, nodelay), independent of the backend's own SlowAPI limits.
- Sets the same security headers as the backend's `SecurityHeadersMiddleware` (CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`).
- Forwards `X-Real-IP`, `X-Forwarded-For` (overwritten, not appended — prevents client header spoofing), `X-Forwarded-Proto`, `Host` to the backend.
- Serves the built SPA for `/login`, `/new`, `/manage`, `/profile`, `/admin`, `/expired`, `/links/:code/share`, `/p/:code`; falls through to the backend for anything else (short-code redirects).
- `client_max_body_size 64k`, `server_tokens off`.

HSTS (`Strict-Transport-Security: max-age=31536000; includeSubDomains`) is set by nginx on every response. The backend itself never sets it — it only terminates HTTP — and its startup logs a warning as a reminder that nginx (or an equivalent TLS-terminating layer) must be in front of it in any deployment that skips this Compose stack's frontend container.
