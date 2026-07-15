# API Reference

Base path in production: requests go through nginx, which proxies `/api/*` to the backend. In dev with `APP_ENV=development`, interactive docs are available at `/docs` and `/redoc` (disabled in production).

Auth, CSRF, and JWT lifecycle details (cookie flags, token revocation tradeoffs, password policy) are documented in [SECURITY.md](../SECURITY.md) — this file only lists endpoint shapes and rate limits.

## Auth — `/api/auth`

| Method | Path | Auth required | Rate limit | Request | Response |
|---|---|---|---|---|---|
| POST | `/register` | None | 5/min | `UserCreate` (email, password) | `UserOut`, 201 |
| POST | `/login` | None | 5/min | OAuth2 form (`username`, `password`) | `Token` `{token_type: "bearer"}`, sets `access_token` cookie |
| POST | `/logout` | None | — | — | `{"message": "Logged out"}`, clears cookie |
| GET | `/me` | Cookie or bearer | 60/min | — | `UserOut` |
| PATCH | `/me` | Cookie or bearer | 10/min | `UserUpdate` (username) | `UserOut` |
| PATCH | `/me/email` | Cookie or bearer | 10/min | `EmailChange` (current_password, new_email) | `UserOut` |
| PATCH | `/me/password` | Cookie or bearer | 10/min | `PasswordChange` (current_password, new_password) | `Token` `{token_type: "bearer"}`, rotates `access_token` cookie |
| POST | `/users` | Cookie/bearer + admin | 10/min | `UserCreate` | `UserOut`, 201 |

Notes:
- `/register` is gated by the `ALLOW_REGISTRATION` env var (default: disabled — returns `403` unless set to `true`/`1`/`yes`/`on`).
- `/login` accepts either email or username in the `username` form field (routed by presence of `@`).
- `username` in `/me` PATCH must match `^[a-zA-Z0-9_-]+$`, 1-50 chars, and be unique.
- `/me/email` and `/me/password` both require `current_password` (401 if wrong). No email verification flow — the change is immediate, same as registration.
- `/me/password` revokes the caller's current JWT via the token blocklist and issues a fresh `access_token` cookie in the same response, so the current session stays authenticated while any other copy of the old token is rejected immediately.
- `/users` (admin-only user creation) does not check `ALLOW_REGISTRATION`.

## URLs — `/api/urls`

| Method | Path | Auth required | Rate limit | Request | Response |
|---|---|---|---|---|---|
| POST | `` (i.e. `/api/urls`) | Cookie/bearer | 20/min | `URLCreate` | `URLOut`, 201 |
| GET | `` | Cookie/bearer | 100/min | — | `URLOut[]` |
| PATCH | `/{url_id}` | Cookie/bearer | 30/min | `URLUpdate` (short_code, password, remove_password, expires_at) | `URLOut` |
| DELETE | `/{url_id}` | Cookie/bearer | 30/min | — | 204, no body |
| POST | `/{short_code}/unlock` | None | 10/min | `PasswordVerify` (password) | `UnlockOut` `{redirect_url}` |
| GET | `/{url_id}/stats` | Cookie/bearer | 60/min | — | `StatsOut` |
| GET | `/{short_code}/qr` | Cookie/bearer | 60/min | — | `image/png` |

Notes:
- All URL operations except `unlock` are scoped to the authenticated user — `GET`/`PATCH`/`DELETE`/`stats`/`qr` only see/affect rows where `user_id` matches the caller; otherwise `404`.
- `original_url` is SSRF-checked synchronously on create; resolves to a private/loopback/reserved/link-local/multicast address → `422`. Transient DNS failure → `503`.
- `custom_code`/`short_code`, if provided, must be unique (`409` if taken), match `^[a-zA-Z0-9_-]+$`, and must not be one of the frontend's reserved SPA routes: `login`, `new`, `manage`, `profile`, `admin`, `expired` (`422` — shadowed by the SPA shell and would never reach the redirect route). If `custom_code` is omitted on create, an 8-char random alphanumeric code is generated (`services/auth.py::get_unique_short_code`, retries up to 10 times, `503` on exhaustion).
- `expires_at`, if provided, must be in the future (`422` otherwise).
- `original_url` is capped at 2048 characters.
- `PATCH /{url_id}` always requires `short_code` in the body (re-validated for uniqueness/reserved-word if changed); `remove_password: true` clears the password, otherwise a non-empty `password` sets/replaces it.
- `POST /{short_code}/unlock` verifies a password-protected link's password and returns the real destination for the frontend to redirect to; it also logs a `Click` row. `410` if the link has expired, `400` if not password-protected or the destination now fails the SSRF re-check, `401` on wrong password.
- `GET /{short_code}/qr` renders a PNG QR code (via `segno`) encoding the short link built from `request.base_url`.

## Admin — `/api/admin`

| Method | Path | Auth required | Rate limit | Request | Response |
|---|---|---|---|---|---|
| GET | `/users` | Cookie/bearer + admin | 60/min | — | `AdminUserOut[]` |
| PATCH | `/users/{user_id}` | Cookie/bearer + admin | 30/min | `AdminUserUpdate` (is_admin) | `AdminUserOut` |
| DELETE | `/users/{user_id}` | Cookie/bearer + admin | 30/min | — | 204, no body |

Notes:
- All endpoints require `is_admin`; non-admins get `403`, unauthenticated callers get `401`.
- `GET /users` returns every user with a `url_count` (number of URLs they own).
- `PATCH /users/{user_id}` sets the target user's `is_admin` flag; an admin cannot change their own role (`400`).
- `DELETE /users/{user_id}` cascades: the user's URLs and their click rows are removed.
- An admin cannot delete their own account (`400`); a missing target user returns `404` on either endpoint.

## Redirect — no prefix

| Method | Path | Auth required | Rate limit | Response |
|---|---|---|---|---|
| GET | `/{short_code}` | None | 60/min | `302` to `original_url`, or `404`/`400`/`503` |

- Re-runs the SSRF check at redirect time (5s timeout) to catch DNS rebinding since creation. Blocked or now-invalid destination → `400`. DNS timeout/failure → `503`.
- Every successful redirect inserts a `Click` row with anonymized IP and truncated/sanitized User-Agent.
- `short_code` path param is constrained to `^[a-zA-Z0-9_-]+$`, max 16 chars.

## Health

| Method | Path | Auth required | Rate limit | Response |
|---|---|---|---|---|
| GET | `/health` | None | 30/min | `{"status": "ok"}` |
| GET | `/api/health` | None | 60/min | `{"status": "ok"}` |

Same payload; `/api/health` is mounted so the frontend can reach it through nginx's `/api/*` proxy rule (used to poll backend connectivity) without hitting the internal-only `/health` path directly.

## Schemas

```
UserCreate    { email: EmailStr, password: str (12-128 chars) }
UserOut       { email: str, created_at: datetime, is_admin: bool, username: str | null }
UserUpdate    { username: str (1-50 chars, ^[a-zA-Z0-9_-]+$) }
EmailChange   { current_password: str, new_email: EmailStr }
PasswordChange { current_password: str, new_password: str (min 12 chars; endpoint also caps at 128) }
AdminUserOut  { id: int, email: str, username: str | null, is_admin: bool, created_at: datetime, url_count: int }
AdminUserUpdate { is_admin: bool }
Token         { token_type: "bearer" }

URLCreate     { original_url: AnyHttpUrl (≤2048 chars), custom_code: str | null (6-16 chars, ^[a-zA-Z0-9_-]+$, not reserved), password: str | null (6-128 chars), expires_at: datetime | null (must be future) }
URLUpdate     { short_code: str (3-16 chars, ^[a-zA-Z0-9_-]+$, not reserved), password: str = "", remove_password: bool = false, expires_at: datetime | null (must be future) }
URLOut        { id: int, short_code: str, original_url: str, created_at: datetime, click_count: int, has_password: bool, expires_at: datetime | null }
PasswordVerify { password: str (6-128 chars) }
UnlockOut     { redirect_url: str }
StatsOut      { url_id: int, short_code: str, original_url: str, total_clicks: int, clicks_by_date: dict[str, int] }
```

`UserOut` never includes `password_hash`. Login never returns the JWT in the response body — it's set only as an HttpOnly cookie.
