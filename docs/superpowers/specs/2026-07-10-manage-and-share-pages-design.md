# Manage & Share Pages — Design

## Problem

`DashboardView.vue` currently does two unrelated jobs on one page: creating a
new short link (`CreateURLForm`) and managing existing ones (list, edit,
stats, delete, QR). There's no dedicated place to land right after creating a
link, and no way to revisit a link's QR/copy/share options later without
re-opening the management list's QR dialog.

## Scope

**In scope:** splitting Dashboard into a create page and a management page,
adding a new share page, updating navigation and the create-success flow to
point at it.

**Out of scope:** any backend changes (the share page reuses the existing
`GET /api/urls` list and QR endpoint — no new endpoint), editing
`original_url` from the management page (unchanged from today), bulk actions
on the management page.

## Routes

| Path | Name | Component | Auth | Title |
|---|---|---|---|---|
| `/` | — | redirect | — | → `/manage` |
| `/new` | `new-link` | `NewLinkView.vue` (new) | `requiresAuth` | New Link |
| `/manage` | `manage` | `ManageView.vue` (renamed from `DashboardView.vue`) | `requiresAuth` | Manage Links |
| `/links/:code/share` | `share` | `ShareView.vue` (new) | `requiresAuth` | Share Link |
| `/profile`, `/admin`, `/p/:code`, `/expired` | unchanged | unchanged | unchanged | unchanged |

`/` currently redirects to `/dashboard`; this changes it to redirect to
`/manage` so returning users land on their link list, not an empty create
form.

## Components

### `frontend/src/views/NewLinkView.vue` (new)

Small wrapper: `AppNavbar` + `CreateURLForm`. Nothing else — no local state
beyond what `AppNavbar`/`CreateURLForm` already own.

### `frontend/src/views/ManageView.vue` (renamed from `DashboardView.vue`)

Everything `DashboardView.vue` has today, minus:
- The `<CreateURLForm />` usage (moved to `NewLinkView.vue`).
- The QR dialog (`qrDialogRef`, `qrShortCode`, `qrSrc`, `handleQr`, `closeQr`,
  and the `<dialog class="qr-dialog">` markup) — replaced by a "Share"
  button that navigates to `/links/:code/share` instead of opening a modal.

Everything else (delete confirm dialog, edit dialog with short code/
password/expiry, stats panel, `URLCard` list) stays as-is.

### `frontend/src/views/ShareView.vue` (new)

Reads `route.params.code`. On mount, if `urlsStore.urls` is empty, calls
`urlsStore.fetchAll()` first (covers direct navigation / page refresh, since
there's no single-link GET endpoint — the app already fetches the full list
everywhere else, e.g. `handleEdit`'s `urlsStore.urls.find(...)` in
`DashboardView.vue` today). Then looks up
`urlsStore.urls.find(u => u.short_code === code)`.

- **Found:** renders the full short URL (`BASE_URL + '/' + short_code`) with
  a copy-to-clipboard button (`navigator.clipboard.writeText`, with a
  transient "Copied!" confirmation state), the QR image
  (`urlsApi.qrUrl(code)` as an `<img>`, same endpoint the old QR dialog
  used), a native share button (`navigator.share({ title, url })`, rendered
  only when `navigator.share` exists — feature-detected, no polyfill), two
  social share links (X/Twitter intent URL, WhatsApp `wa.me` link — plain
  `<a href>` tags, no SDK or API key), and a "Back to Manage" link to
  `/manage`.
- **Not found:** "Link not found" message with a link back to `/manage`
  (covers a deleted link, a link belonging to another user, or a bad code in
  the URL bar).

### `frontend/src/components/URLCard.vue`

`qr` emit renamed to `share` (still carries the short code). Button label
"QR" → "Share". `ManageView.vue`'s handler navigates
(`router.push({ name: 'share', params: { code } })`) instead of opening the
old QR dialog.

### `frontend/src/components/CreateURLForm.vue`

On successful create, instead of resetting the four local fields
(`originalUrl`/`customCode`/`password`/`expiresAt`), calls
`router.push({ name: 'share', params: { code: created.short_code } })`. The
component unmounts on navigation, so resetting local state it's about to
lose is dead code — dropped, not kept alongside the redirect.

### `frontend/src/components/AppNavbar.vue`

Drawer links become: Manage, New Link, Profile, (Admin, if `is_admin`), Sign
out — same contextual "hide the link to whichever page you're already on"
pattern already in place, just two entries instead of one (previously just
"Dashboard").

## Testing

- **Router:** update `meta.title`/guard tests for the `/new`, `/manage`,
  `/links/:code/share` routes (all `requiresAuth: true`, so they follow the
  existing guard behavior already tested).
- **`NewLinkView.spec.ts`** (new): renders `AppNavbar` and `CreateURLForm`.
- **`ManageView.spec.ts`** (renamed from `DashboardView.spec.ts`): drop the
  create-form-specific assertions (now covered by `CreateURLForm.spec.ts`
  and `NewLinkView.spec.ts`) and the QR-dialog tests; add a test that
  clicking "Share" on a `URLCard` navigates to `/links/:code/share`.
- **`ShareView.spec.ts`** (new): renders short URL + copy button; copy
  button calls the clipboard API; renders the QR image with the correct
  `src`; native share button only renders when `navigator.share` is defined;
  social links have the correct `href`; "Link not found" state when the code
  doesn't match any URL in the store; calls `fetchAll()` when the store is
  empty on mount, skips it when already populated.
- **`CreateURLForm.spec.ts`**: replace the "clears form fields after
  successful creation" test with one asserting `router.push` is called with
  `{ name: 'share', params: { code: <created short_code> } }`.
- **`AppNavbar.spec.ts`**: update the nav-link assertions for the new
  Manage/New Link entries and their contextual hiding.
