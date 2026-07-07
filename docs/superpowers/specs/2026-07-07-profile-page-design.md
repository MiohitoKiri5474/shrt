# Profile Page — Design

## Purpose

Give users a dedicated page to change their username, email, and password. Today, only username is editable, via an inline click-to-edit widget buried in the dashboard's hamburger dropdown. Email and password have no change path at all post-registration.

## Current state (context)

- `User` model (`backend/src/app/models.py`): `email`, `username` (nullable, unique), `password_hash`, `is_admin`, `created_at`. No other profile fields.
- `PATCH /api/auth/me` already exists (`backend/src/app/routers/auth.py`), username-only, backed by `UserUpdate` schema (`username: str` with `^[a-zA-Z0-9_-]+$`, 1-50 chars). Keep as-is.
- No email-change or password-change endpoint exists yet.
- No email-sending infrastructure exists (no SMTP/SendGrid/etc. found in the backend) — email change will be immediate and unverified, matching how registration itself already works (no verification email sent there either).
- `services/auth.py` provides `hash_password_async` / `verify_password_async` (bcrypt + SHA-256 prehash) and `create_access_token` (JWT with `jti`, `exp`, `sub`).
- `services/token_blocklist.py` provides a Redis-backed revocation store (`revoke(jti, ttl)` / `is_revoked(jti)`), currently used only by `/logout`.
- Frontend: `DashboardView.vue` has an inline username editor in its hamburger dropdown (`editingUsername`, `usernameInput`, `startEditUsername`, `saveUsername`). `AdminView.vue` establishes the pattern for a secondary page: header with title + hamburger containing a "← Dashboard" back-link + theme toggle.
- Established codebase convention: per-action error/success state as separate refs (e.g. `AdminView.vue`'s `roleError`, `deleteError`, `loadError` are three distinct refs, not one shared error object).

## Scope

In scope:
- Change username (existing endpoint, reused as-is)
- Change email (new endpoint)
- Change password (new endpoint)
- New `/profile` route and `ProfileView.vue`
- Remove the inline username editor from `DashboardView.vue`'s hamburger dropdown; replace with a "Profile" link

Out of scope (not requested, not building):
- Email verification / confirmation links (no email infra exists; out of scope for this change)
- Avatar/profile picture, bio, or any other new profile field
- Account deletion from the profile page (already exists via admin-only user management)
- Changing `is_admin` from the profile page (admin-only, already handled in `AdminView.vue`)

## Backend design

### `PATCH /api/auth/me/email`

Request: `{ current_password: str, new_email: EmailStr }`
Response: `UserOut` (200)

Logic (mirrors `_create_user`'s uniqueness check and `login`'s password verification):
1. `verify_password_async(current_password, current_user.password_hash)` — 401 `"Incorrect password"` on failure.
2. Check `new_email` not already taken by another user (`SELECT ... WHERE email = new_email AND id != current_user.id`) — 409 `"Email already registered"` on conflict.
3. Update `current_user.email`, commit. Catch `IntegrityError` as a race-condition fallback to the same 409 (same pattern `update_me` already uses for username).

Rate limit: `10/minute` (same as `update_me`).

### `PATCH /api/auth/me/password`

Request: `{ current_password: str, new_password: str }` (`new_password` reuses `UserCreate`'s min-length validator: 12 chars minimum; 128-char cap enforced separately at the endpoint, see below)
Response: `{ token_type: "bearer" }` (200) — same shape as `login`, and a new `access_token` cookie is set, since the old token is being revoked in the same request.

Logic:
1. If `len(new_password) > 128`, 422 `"Password too long"` — same manual cap `register` applies at the endpoint level (not a schema field constraint there either).
2. `verify_password_async(current_password, current_user.password_hash)` — 401 `"Incorrect password"` on failure.
3. `current_user.password_hash = await hash_password_async(new_password)`, commit.
4. Revoke the caller's current token: decode the request's own cookie/bearer token (same extraction the `logout` endpoint uses), compute remaining TTL from `exp`, call `blocklist.revoke(jti, ttl)`. This mirrors `logout`'s revocation exactly.
5. Issue a fresh `access_token` cookie via `create_access_token({"sub": str(current_user.id)})` and `response.set_cookie(...)` (same cookie flags as `login`), so the current browser tab keeps working without a re-login, while any other copy of the old token (other tabs, a stolen cookie) is immediately rejected.

Rate limit: `10/minute`.

### Schemas (`backend/src/app/schemas.py`)

```python
class EmailChange(BaseModel):
    current_password: str
    new_email: EmailStr

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        return v
```

(`password_min_length` duplicates `UserCreate`'s validator; acceptable, matches how `register`'s 128-char cap is also duplicated inline rather than shared today — not introducing a new shared-validator abstraction for two call sites.)

## Frontend design

### New route: `/profile` → `ProfileView.vue`

Registered in the router alongside the existing `/dashboard`, `/admin` routes, same auth guard (must be logged in).

### `ProfileView.vue` structure

Header: same shape as `AdminView.vue`'s (`<h1>Profile</h1>` + `<nav>` with hamburger containing a "← Dashboard" `RouterLink`, plus the theme-toggle button outside the hamburger — matching the button-order fix already landed in `AdminView.vue`).

Body: three independent `<section>` cards, each a self-contained form:

1. **Username** — reuses the existing `PATCH /me` call. Input + Save button. `usernameError` / `usernameSuccess` refs.
2. **Email** — current email shown, "current password" + "new email" inputs, Save button. `emailError` / `emailSuccess` refs.
3. **Password** — "current password" + "new password" + "confirm new password" inputs (confirm is a client-side-only check, not sent to the server), Save button. `passwordError` / `passwordSuccess` refs. On success, no redirect needed — the new cookie from the response keeps the session alive.

Each section clears its own error/success on submit, independent of the other two — a failure in one does not block or clear the others, matching the "separate refs per concern" convention.

### `DashboardView.vue` changes

Remove: `editingUsername`, `usernameInput`, `usernameError`, `startEditUsername`, `saveUsername`, and the inline `<template v-if="editingUsername">` editor block in the hamburger dropdown.

Replace with: plain-text username display (no click affordance) plus a new `RouterLink` to `/profile` labeled "Profile", placed in the dropdown above the existing "Admin" link (visible to all users, not just admins).

## Error handling

- All three endpoints: 401 on wrong `current_password` (generic message, no distinction from "user not found" to avoid enumeration), 409 on taken email/username, 422 on schema validation (short password, malformed email, invalid username chars).
- Frontend: each section shows its own inline error message on failure (matching `AdminView.vue`'s `role="alert"` pattern) and a transient success message (matching `AdminView.vue`'s `successMessage` + `setTimeout` clear pattern already used for "User X created.").
- Password-change specifically: if the fresh-cookie step fails for any reason after the DB commit succeeds, the user's password is still changed correctly (source of truth is the DB) — worst case they're logged out and must log back in with the new password, not a data-loss scenario.

## Testing plan

Backend (`backend/tests/`):
- `test_update_email`: happy path, wrong password → 401, duplicate email → 409, malformed email → 422.
- `test_update_password`: happy path (verify new password logs in, old password no longer works), wrong current password → 401, short new password → 422, old `jti` is rejected by `get_current_user` after change (blocklist integration), new cookie from the response allows a follow-up authenticated request without re-login.

Frontend (`frontend/src/views/__tests__/`):
- New `ProfileView.spec.ts`: each of the 3 sections — success path (shows success message, form resets where applicable), error path (shows the section's own error, other sections unaffected), loading/disabled-button state during submit.
- Update `DashboardView.spec.ts`: remove the now-deleted inline-username-edit test cases, add a test asserting a "Profile" link exists in the hamburger dropdown and navigates to `/profile`.
