# Shared Navbar Rebuild — Design

## Problem

The app header (brand, page title, theme toggle, hamburger menu) is duplicated
with drift across four views: `DashboardView.vue`, `AdminView.vue`,
`ProfileView.vue`, `LoginView.vue`. Each copy has its own `showMenu`/`menuRef`
state, its own dropdown-menu markup, and inconsistent dropdown contents
(Dashboard's dropdown has Profile/Admin/Sign out; Admin's and Profile's only
have a "← Dashboard" link). The hamburger opens a small anchored dropdown,
not the side drawer the product now wants.

## Scope

**In scope:** `DashboardView`, `AdminView`, `ProfileView`, `LoginView`.

**Out of scope:** `PasswordGateView`, `ExpiredView`. These currently have no
header/navbar at all (standalone cards for unauthenticated short-link
visitors) and stay that way — adding one would be new scope, not a rebuild.

## Component: `frontend/src/components/Navbar.vue`

A single shared component replacing the duplicated header markup. No
required props — it reads state directly:

- `useRoute()` — page title comes from `route.meta.title`
- `useAuthStore()` — `isAuthenticated`, `user` (email/username, `is_admin`),
  and owns the sign-out action
- `useThemeStore()` — theme toggle state/action

Optional named slot `status`, used only by `DashboardView` to project
`NetworkStatusIndicator` into the navbar (it doesn't belong in the other
three pages and isn't one of the four core navbar items).

### Router changes

Add `meta.title` to the four in-scope routes in `frontend/src/router/index.ts`:

| route | title |
|---|---|
| `/login` | `Log in` |
| `/dashboard` | `Dashboard` |
| `/profile` | `Profile` |
| `/admin` | `User Management` |

`/p/:code` and `/expired` are untouched (no navbar, no title needed).

## Layout

Header is a 3-cell CSS grid: `grid-template-columns: 1fr auto 1fr`.

- **Left cell:** `Shrt` brand, a `RouterLink` to `/` (root redirects to
  `/dashboard`, and the existing nav guard bounces unauthenticated users to
  `/login` from there — no special-casing needed in the link itself).
- **Center cell:** current page title (`route.meta.title`), truly centered
  regardless of how wide the left/right cell contents are, since both outer
  tracks are `1fr`.
- **Right cell:** `status` slot (Dashboard only) → theme toggle → hamburger
  button, in that order, right-aligned.

The hamburger button itself does not render when `!authStore.isAuthenticated`
(i.e., on `LoginView`) — there are no nav links to show pre-auth, so no
button, not an empty/disabled one.

## Side drawer

Replaces the old anchored `.dropdown-menu`. A fixed-position panel sliding in
from the right, with a backdrop overlay behind it.

- `role="dialog" aria-modal="true" aria-label="Navigation menu"`
- Opens on hamburger click (`aria-expanded`/`aria-haspopup` preserved on the
  button, matching current a11y pattern)
- Closes on: backdrop click, `Esc`, an explicit `✕` close button inside the
  drawer, or clicking any link inside it
- No focus trap — matches the current dropdown's complexity level; existing
  dropdowns don't trap focus either, and Esc + backdrop-click already cover
  the keyboard/pointer dismissal cases.

### Drawer contents (identical on every authenticated page)

1. User display: `authStore.user?.username ?? authStore.user?.email`
2. Separator
3. `Dashboard` link — hidden when `route.name === 'dashboard'`
4. `Profile` link — hidden when `route.name === 'profile'`
5. `Admin` link — shown only when `authStore.user?.is_admin`, hidden when
   `route.name === 'admin'`
6. Separator
7. `Sign out` button

This is a behavior change for `AdminView`/`ProfileView`: their drawers
currently only have a "← Dashboard" link; now they get the full contextual
set, matching what `DashboardView` already shows. Confirmed as intended.

## Migration

Remove from `DashboardView.vue`, `AdminView.vue`, `ProfileView.vue`,
`LoginView.vue`:

- Header/nav template markup (`<header>`, `.dash-nav`/`.admin-nav`/etc.,
  theme-toggle button, hamburger button, dropdown-menu block)
- Script state: `showMenu`, `menuRef`, `handleOutsideClick` (+ its
  `onMounted`/`onBeforeUnmount` listeners), `handleLogout`
- Associated scoped CSS for all of the above

Each view instead renders `<Navbar>` at the top of its template.
`DashboardView` passes `<NetworkStatusIndicator />` into the `status` slot.

## Testing

New `frontend/src/components/__tests__/Navbar.spec.ts`:

- Brand renders as a link to `/`
- Title text matches `route.meta.title` for a few mounted routes
- Theme toggle click calls `themeStore.toggle()`
- Hamburger button absent when `authStore.isAuthenticated` is `false`
- Hamburger click opens the drawer; backdrop click / Esc / ✕ / link-click
  close it
- Drawer shows the correct contextual link set for an admin user, a
  non-admin user, and while already on each of the three authenticated pages
- Sign out calls `authStore.logout()` then redirects to `/login`

Update `DashboardView.spec.ts`, `AdminView.spec.ts`, `ProfileView.spec.ts`,
`LoginView.spec.ts`: remove now-dead assertions against the old inline
header/dropdown markup; keep/add an assertion that the view renders
`<Navbar>` (or its rendered title) so page-level tests still confirm the
right title shows.
