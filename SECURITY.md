# Security

This document describes the security posture of the URL Shortener project and records
architectural decisions that have security implications. It is intended for developers
who maintain or extend the codebase.

---

## CSRF Protection

### Current Approach

Cross-Site Request Forgery (CSRF) is currently mitigated by using Bearer tokens
transmitted via the `Authorization` HTTP header (see
`frontend/src/api/client.ts`).

The browser's Same-Origin Policy (SOP) prevents cross-origin pages from setting
custom request headers. Because the `Authorization: Bearer <token>` header is a
non-simple, custom header, a malicious page on another origin cannot include it in a
forged request. Every authenticated request reaching the backend therefore must have
originated from JavaScript running on the legitimate frontend origin.

Token storage: the access token is kept in `localStorage` and attached to each request
by an Axios interceptor (`apiClient.interceptors.request.use`).

### Why This Works (and When It Stops Working)

| Condition | CSRF risk |
|---|---|
| Token in `localStorage`, sent via `Authorization` header (current state) | Low — cross-origin requests cannot set the header |
| Token in a regular (non-HttpOnly) cookie, sent automatically by browser | High — browser sends cookies cross-origin regardless of SOP |
| Token in an HttpOnly cookie | High — same as above; JS cannot read it but the browser still attaches it |

### Migration Warning

**If token storage is ever migrated to HttpOnly cookies**, the Bearer-header defense
no longer applies and CSRF becomes a genuine risk. Before or at the same time as that
migration, one of the following mitigations MUST be added:

1. **Synchronizer Token Pattern** — include a CSRF token in a non-cookie header (e.g.,
   `X-CSRF-Token`) and validate it server-side.
2. **Double-Submit Cookie** — set a separate CSRF cookie that is also sent as a request
   header; the server verifies both values match.
3. **SameSite cookie attribute** — set the session cookie with `SameSite=Strict` or
   `SameSite=Lax` to prevent cross-site submission (effective in modern browsers;
   verify support for your target browser matrix before relying on this alone).

The relevant files that must be updated during such a migration are:

- `frontend/src/api/client.ts` — Axios interceptor that attaches the token
- `frontend/src/api/auth.ts` — authentication API calls
- `frontend/src/api/urls.ts` — URL management API calls
- Backend authentication middleware / route guards

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
