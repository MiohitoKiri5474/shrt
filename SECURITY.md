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

## Password Policy

Passwords are required to be between 12 and 128 characters (enforced at registration).
bcrypt is used for hashing with a cost factor of 12.

---

## User-Agent Header Truncation

The `User-Agent` header captured during click tracking is capped at 512 characters to
prevent excessively long strings from being stored in the database.

---

## Reporting a Vulnerability

If you discover a security vulnerability, please open a GitHub issue marked
**[SECURITY]** or contact the maintainers directly. Do not publicly disclose details
until a fix has been released.
