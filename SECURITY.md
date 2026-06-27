# Security

This document describes the security posture of the URL Shortener project and records
architectural decisions that have security implications. It is intended for developers
who maintain or extend the codebase.

---

## CSRF Protection

### Current Approach

Authentication uses **HttpOnly cookies** set by the backend on successful login
(`backend/src/app/routers/auth.py`). The cookie is configured with:

- `HttpOnly=True` — JavaScript cannot read it, preventing XSS-based token theft
- `SameSite=Strict` — the browser will not attach the cookie to any cross-site request,
  including navigations from external pages
- `Secure=True` in production (`APP_ENV != development`) — cookie transmitted only over HTTPS

The frontend uses `withCredentials: true` on all Axios requests so the browser includes
the cookie automatically. No `Authorization` header or `localStorage` is involved.

### Why This Works

`SameSite=Strict` is the active CSRF mitigation. A malicious page on a different origin
cannot trigger a state-changing request that carries the session cookie because the
browser refuses to attach `SameSite=Strict` cookies to cross-origin requests.

| Condition | CSRF risk |
|---|---|
| `SameSite=Strict` HttpOnly cookie (current state) | Low — browser blocks cross-site cookie attachment |
| `SameSite=Lax` cookie | Low for non-idempotent requests; moderate for top-level GET navigations |
| No `SameSite` / `SameSite=None` cookie | High — browser sends cookies cross-origin |
| Token in `localStorage`, sent via `Authorization` header | Low — cross-origin scripts cannot set custom headers |

### Relevant Files

- `backend/src/app/routers/auth.py` — sets and clears the `access_token` cookie
- `frontend/src/api/client.ts` — Axios instance with `withCredentials: true`
- `frontend/src/api/auth.ts` — authentication API calls

---

## JWT Token Lifecycle and Logout Invalidation

### Current Behaviour

Access tokens are short-lived JWTs (15-minute expiry) stored in an **HttpOnly, SameSite=Strict
cookie**. Every issued token carries a `jti` (JWT ID) claim — a cryptographically random
32-character hex token generated at mint time via `secrets.token_hex(16)`.

On logout (`POST /api/auth/logout`), the backend:

1. Clears the `access_token` cookie via `response.delete_cookie()`.
2. Extracts the `jti` and remaining TTL from the token.
3. Writes `revoked_jti:<jti> = 1` to Redis via `SETEX` with the remaining TTL so the
   entry auto-expires exactly when the token itself would have expired.

On every authenticated request, `get_current_user` checks the `jti` against the Redis
blocklist before touching the database. Tokens whose `jti` is found in the blocklist are
rejected with `HTTP 401 Token has been revoked`.

### Fail-Open Behaviour When Redis Is Unavailable

The blocklist is defence-in-depth, not the primary access control. If Redis is unreachable,
both `revoke` and `is_revoked` fail open (log a warning, return without raising). This means:

- **During a Redis outage**, a previously revoked token may temporarily regain validity —
  but only for its remaining `<= ACCESS_TOKEN_EXPIRE_MINUTES` window, and only while Redis
  is down.
- **Failing closed** (rejecting every authenticated request on Redis errors) would be a
  self-inflicted denial of service. The short token lifetime bounds the risk of failing open.

When `REDIS_URL` is not set, the application uses `NullTokenBlocklist`, which is a no-op
implementation: logout still clears the cookie and authentication still works, but a stolen
token cannot be invalidated server-side. A warning is logged when this fallback is selected.
In production, `REDIS_URL` is enforced at startup (see startup check in `main.py`).

### Relevant Files

- `backend/src/app/services/auth.py` — `create_access_token()` (adds `jti`) and `decode_token()`
- `backend/src/app/services/token_blocklist.py` — `RedisTokenBlocklist` (production), `NullTokenBlocklist` (fallback)
- `backend/src/app/routers/auth.py` — `logout` endpoint (revokes `jti`), `get_current_user` (checks blocklist)

---

## Password Policy

Passwords are required to be between 12 and 128 characters (enforced at registration).
bcrypt is used for hashing with a cost factor of 12.

---

## User-Agent Header Truncation

The `User-Agent` header captured during click tracking is capped at 512 characters to
prevent excessively long strings from being stored in the database.

---

## Sequential Integer Primary Keys and Row-Count Leakage

### Current State

`User` and `URL` rows use auto-increment integer primary keys (`id: int`). Sequential IDs
expose two risks:

1. **Enumeration** — an authenticated user can infer how many users or URLs exist by
   observing their own ID returned in responses (e.g. `URLOut.id` is present in every
   `GET /api/urls` response), and can probe adjacent integer IDs via endpoints such as
   `DELETE /api/urls/{url_id}` and `GET /api/urls/{url_id}/stats`. Ownership checks
   prevent unauthorised access to content, but the IDs themselves are returned directly
   in responses — not merely inferable — so count metadata and ID space are exposed to
   any authenticated user.
2. **Scraping** — authenticated API endpoints expose integer PKs directly: `URLOut.id`
   is returned in list and create responses, `StatsOut.url_id` is returned in stats
   responses, and path parameters on `DELETE /api/urls/{url_id}` and
   `GET /api/urls/{url_id}/stats` accept sequential integer IDs. An authenticated user
   can infer the approximate total URL count from their own URL IDs and probe adjacent
   IDs to confirm existence. (`GET /<short_code>` uses random alphanumeric codes and
   does not expose integer IDs.)

### Accepted State / Planned Migration

Replacing integer PKs with UUIDs (or ULID/KSUID) is the correct long-term fix but requires:

- A database migration that changes the PK column type and regenerates all existing IDs.
- Updates to every foreign key referencing those columns (`URL.user_id`, `Click.url_id`).
- Coordination with any running sessions or cached tokens that embed the numeric ID (the
  JWT `sub` claim currently carries the integer user ID).

This is a **planned migration** and not an emergency fix. The ownership checks on
authenticated endpoints provide the primary access-control boundary and prevent
unauthorised access to content. However, integer PKs are returned directly in API
responses (`URLOut.id`, `StatsOut.url_id`) and accepted in path parameters, so any
authenticated user can observe ID values and infer approximate row counts. The migration
will be tracked separately.

### Path to UUID PKs

1. Add `uuid` default to `User.id`, `URL.id`, and `Click.id` in `models.py`.
2. Write an Alembic migration that alters PK and FK columns and backfills UUIDs.
3. Update `get_current_user` to decode a UUID `sub` from JWT tokens.
4. **Invalidate** all existing sessions after deployment — do not just rotate them.
   Existing tokens carry an integer `sub` claim and `get_current_user` currently calls
   `int(payload.get("sub"))`, so any token issued before the migration will be
   incompatible. Recommended cut-over approaches: add a `token_version` claim to JWTs
   and increment the version in the user record on migration (any token with the old
   version is rejected), or maintain a short-lived `revoked_tokens` blacklist keyed on
   `jti` covering the token expiry window surrounding the migration.

### Relevant Files

- `backend/src/app/models.py` — `User` and `URL` model definitions
- `backend/src/app/routers/auth.py` — `get_current_user` decodes `sub` as int

---

## Reporting a Vulnerability

If you discover a security vulnerability, please open a GitHub issue marked
**[SECURITY]** or contact the maintainers directly. Do not publicly disclose details
until a fix has been released.
