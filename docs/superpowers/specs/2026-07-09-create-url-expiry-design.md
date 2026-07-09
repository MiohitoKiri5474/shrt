# Create-URL Expiry Input — Design

## Problem

`expires_at` can only be set on an existing link, via the Dashboard's edit
dialog (`URLUpdate`). The create flow (`URLCreate`, `CreateURLForm.vue`) has
no expiry field, so setting one at creation time requires two round trips:
create the link, then immediately edit it.

## Scope

**In scope:** `CreateURLForm.vue`, `URLCreate` schema, `create_url` endpoint,
`urlsStore.create()`, `urlsApi.create()`.

**Out of scope:** the edit-dialog expiry field (`DashboardView.vue`) — already
works, untouched. No UI redesign of the create form beyond adding the one
field.

## Backend

### `backend/src/app/schemas.py`

- Add `expires_at: datetime | None = None` to `URLCreate`.
- `URLUpdate` already has a `@field_validator("expires_at", mode="after")`
  enforcing "must be in the future" (`expires_must_be_future`). Extract that
  validator function so both `URLCreate` and `URLUpdate` reuse it instead of
  duplicating the same rule — the two schemas apply the same field validator
  to the same field name/type.

### `backend/src/app/routers/urls.py` — `create_url`

Currently the `URL(...)` constructor omits `expires_at` entirely (defaults to
`None` at the DB layer). Add `expires_at=data.expires_at` to that constructor
call. No other logic in `create_url` changes — SSRF check, custom-code
uniqueness, password hashing all stay as-is.

## Frontend

### `frontend/src/components/CreateURLForm.vue`

Add a third optional field, styled identically to the existing custom-code
and password fields:

```html
<div class="field">
  <label for="expires-at">Expires at (optional)</label>
  <input id="expires-at" v-model="expiresAt" type="datetime-local" />
</div>
```

No client-side "must be future" validation and no `:min` attribute — the
existing edit-dialog expiry input (`DashboardView.vue:227`) has neither, so
this stays consistent with that established pattern. A past-datetime submit
is caught server-side and surfaces through the form's existing generic
catch-all error (`'Failed to create URL.'`), the same way an already-taken
custom code or any other create-time validation failure does today.

On successful create, `expiresAt` resets to `''` alongside the other two
fields (mirrors existing `originalUrl`/`customCode`/`password` reset).

### `frontend/src/stores/urls.ts`

`create()` gains a fourth optional parameter:

```ts
async function create(originalUrl: string, customCode?: string, password?: string, expiresAt?: string)
```

Passed straight through to `urlsApi.create()`.

### `frontend/src/api/urls.ts`

`create()` gains the same fourth parameter, converted to ISO the same way
`DashboardView.vue`'s `confirmEdit` already does it
(`new Date(expiresAt).toISOString()`), and included in the POST body sent to
`URLCreate`. `undefined`/empty string maps to omitting the field (no expiry),
matching how `customCode`/`password` already handle "not provided".

## Testing

- **Backend**: mirror the existing `URLUpdate` expiry tests
  (future value accepted, past value rejected with 422) against `POST
  /api/urls` instead of the update endpoint. Confirm the extracted validator
  is exercised from both schemas (no duplicated test logic, no duplicated
  validator logic).
- **Frontend**: `CreateURLForm.spec.ts` — new test asserting `create()` is
  called with the ISO-converted expiry value when the field is filled, and
  with `undefined` when left blank (mirrors the existing custom-code/password
  "passes X when provided" tests). `stores/urls.spec.ts` and
  `api/urls.spec.ts` (if the latter exists) get the equivalent plumbing
  assertions for the new parameter.
