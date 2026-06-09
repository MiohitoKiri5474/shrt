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
cookie**. On logout (`POST /api/auth/logout`), the backend calls `response.delete_cookie()`,
which instructs the browser to remove the cookie. No server-side token revocation takes place.

### Accepted Tradeoff

This means a token that has been "logged out" of the browser remains cryptographically valid
for up to 15 minutes. An attacker who obtained a copy of the token (e.g., via a server-side
log leak before the HttpOnly flag was enforced) could use it within that window.

We accept this tradeoff because:

- The 15-minute window is short enough for the current threat model.
- HttpOnly cookies prevent JavaScript-based token theft (XSS), which is the most common
  credential-theft vector in web apps.
- Implementing full revocation requires either an in-memory blacklist (lost on restart;
  does not work across multiple processes) or a database / Redis lookup on every
  authenticated request (latency cost, new infrastructure dependency).

### Path to Full Revocation

If the threat model changes (e.g., the app runs behind a load balancer with multiple
replicas, or compliance requirements mandate immediate revocation), add:

1. A `jti` (JWT ID) claim to every issued token (`uuid.uuid4()`).
2. A `revoked_tokens` table (or Redis `SET`) keyed on `jti` with TTL equal to token expiry.
3. A check in `get_current_user` that rejects tokens whose `jti` appears in the revoked set.
4. On logout, insert the token's `jti` into the revoked set.

### Relevant Files

- `backend/src/app/services/auth.py` — `create_access_token()` and `decode_token()`
- `backend/src/app/routers/auth.py` — `logout` endpoint

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
