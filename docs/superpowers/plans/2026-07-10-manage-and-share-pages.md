# Manage & Share Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the Dashboard into a create-only page and a management page, and add a revisitable share page that the create flow redirects to.

**Architecture:** `DashboardView.vue` is renamed to `ManageView.vue` (list/edit/stats/delete, minus the create form and QR dialog) and a new small `NewLinkView.vue` takes over the create form. A new `ShareView.vue` at `/links/:code/share` shows the short URL, QR code, copy button, and share actions — reached both right after creating a link and from a new "Share" button on the management list. No backend changes.

**Tech Stack:** Vue 3 + Vue Router + Pinia + TypeScript + Vitest (frontend only).

## Global Constraints

- No backend changes — reuse existing `GET /api/urls` (list) and `GET /api/urls/{code}/qr`.
- Share page route is `/links/:code/share`, name `share`, dedicated and revisitable (not a one-time post-create-only screen).
- The management page's QR modal is replaced by a "Share" button/link to the share page — not kept alongside it.
- `/` redirects to `/manage` (not `/dashboard`, which no longer exists).
- The old `/dashboard` path is renamed to `/new`, name `new-link`.
- Run frontend tests with `bun run test:unit -- run [path]`; type-check with `bun run type-check`; lint with `bun run lint`.

---

### Task 1: Router — new routes, renamed route, redirect target

**Files:**
- Modify: `frontend/src/router/index.ts`
- Test: `frontend/src/router/__tests__/index.spec.ts`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: route names `new-link` (path `/new`), `manage` (path `/manage`), `share` (path `/links/:code/share`, dynamic param `code`) — every later task's `router.push`/`:to` targets and `RouterLink` targets use these exact names/paths. Root `/` redirects to `/manage`. The `requiresAdmin` guard's non-admin fallback redirects to `/manage` (was `/dashboard`).

- [ ] **Step 1: Write the failing test**

Replace the full contents of `frontend/src/router/__tests__/index.spec.ts` with:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import * as authApiModule from '../../api/auth'
import router from '../index'

vi.mock('../../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
    register: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    updateUsername: vi.fn(),
    updateEmail: vi.fn(),
    updatePassword: vi.fn(),
    addUser: vi.fn(),
  },
}))

describe('router meta titles', () => {
  it.each([
    ['/login', 'Log in'],
    ['/new', 'New Link'],
    ['/manage', 'Manage Links'],
    ['/profile', 'Profile'],
    ['/admin', 'User Management'],
  ])('sets meta.title for %s', (path, expectedTitle) => {
    const match = router.resolve(path)
    expect(match.meta.title).toBe(expectedTitle)
  })
})

describe('router guard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(authApiModule.authApi.me).mockRejectedValue(new Error('401'))
  })

  it('does not call restore() for the public password-gate route when unauthenticated', async () => {
    await router.push('/p/abc123')
    expect(authApiModule.authApi.me).not.toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('password-gate')
  })

  it('does not call restore() for the public expired route when unauthenticated', async () => {
    await router.push('/expired')
    expect(authApiModule.authApi.me).not.toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('expired')
  })

  it('still redirects to login for a requiresAuth route when unauthenticated', async () => {
    await router.push('/manage')
    expect(authApiModule.authApi.me).toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('still redirects admin-only routes away when authenticated non-admin', async () => {
    vi.mocked(authApiModule.authApi.me).mockResolvedValue({
      email: 'a@b.com',
      created_at: '',
      is_admin: false,
      username: null,
    })
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('manage')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun run test:unit -- run src/router/__tests__/index.spec.ts`
Expected: FAIL — `/new` and `/manage` don't resolve to those titles yet (router still has `/dashboard`), and the admin-guard redirect test expects `'manage'` but the router still returns `/dashboard`.

- [ ] **Step 3: Update the router**

Replace the full contents of `frontend/src/router/index.ts` with:

```ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/manage' },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { title: 'Log in' },
    },
    {
      path: '/new',
      name: 'new-link',
      component: () => import('../views/NewLinkView.vue'),
      meta: { requiresAuth: true, title: 'New Link' },
    },
    {
      path: '/manage',
      name: 'manage',
      component: () => import('../views/ManageView.vue'),
      meta: { requiresAuth: true, title: 'Manage Links' },
    },
    {
      path: '/links/:code/share',
      name: 'share',
      component: () => import('../views/ShareView.vue'),
      meta: { requiresAuth: true, title: 'Share Link' },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/ProfileView.vue'),
      meta: { requiresAuth: true, title: 'Profile' },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('../views/AdminView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true, title: 'User Management' },
    },
    {
      path: '/p/:code',
      name: 'password-gate',
      component: () => import('../views/PasswordGateView.vue'),
    },
    {
      path: '/expired',
      name: 'expired',
      component: () => import('../views/ExpiredView.vue'),
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  // Only hydrate auth state for routes that actually need it — calling
  // restore() on public routes (e.g. /p/:code) 401s for anonymous visitors,
  // which trips the global axios interceptor and force-redirects to /login
  // before the public page ever gets to render.
  if ((to.meta.requiresAuth || to.meta.requiresAdmin) && !auth.isAuthenticated) {
    await auth.restore()
  }
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return '/login'
  }
  if (to.meta.requiresAdmin && !auth.user?.is_admin) {
    return '/manage'
  }
})

export default router
```

Note: `NewLinkView.vue`, `ManageView.vue`, and `ShareView.vue` don't exist yet (created in Tasks 5-7) — that's fine, `component: () => import(...)` is a dynamic import that Vite/Vitest doesn't eagerly resolve, so `router.resolve()`/`router.push()` in these tests never actually loads the file.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun run test:unit -- run src/router/__tests__/index.spec.ts`
Expected: PASS, all tests in the file green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/router/index.ts frontend/src/router/__tests__/index.spec.ts
git commit -m "$(cat <<'EOF'
Disclosure: Based on Claude Code generated output.

feat(frontend): add /manage, /new, /links/:code/share routes

Renames /dashboard to /new (create-only, name new-link), adds /manage
(name manage) as the new landing page and link-list route, and adds
/links/:code/share (name share) for the upcoming share page. Root
redirect and the admin-guard non-admin fallback both point at /manage
now. ManageView.vue, NewLinkView.vue, and ShareView.vue are created in
later tasks — the dynamic import() targets don't need to exist yet for
router resolution/guard tests to pass.
EOF
)"
```

---

### Task 2: AppNavbar — Manage + New Link nav entries

**Files:**
- Modify: `frontend/src/components/AppNavbar.vue`
- Test: `frontend/src/components/__tests__/AppNavbar.spec.ts`

**Interfaces:**
- Consumes: route names `manage` (`/manage`) and `new-link` (`/new`) from Task 1 — this task's own spec file uses an independent mock router (doesn't runtime-depend on Task 1), but the names/paths must match Task 1 exactly for the real app to link correctly end to end.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Write the failing test**

Replace the full contents of `frontend/src/components/__tests__/AppNavbar.spec.ts` with:

```ts
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useThemeStore } from '../../stores/theme'
import AppNavbar from '../AppNavbar.vue'

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

vi.mock('../../api/auth', () => ({
  authApi: {
    logout: vi.fn().mockResolvedValue(undefined),
  },
}))

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', name: 'home', component: { template: '<div />' } },
    { path: '/login', name: 'login', component: { template: '<div />' }, meta: { title: 'Log in' } },
    { path: '/new', name: 'new-link', component: { template: '<div />' }, meta: { title: 'New Link' } },
    { path: '/manage', name: 'manage', component: { template: '<div />' }, meta: { title: 'Manage Links' } },
    { path: '/profile', name: 'profile', component: { template: '<div />' }, meta: { title: 'Profile' } },
    { path: '/admin', name: 'admin', component: { template: '<div />' }, meta: { title: 'User Management' } },
  ],
})

const globalOptions = { plugins: [router] }

function setAuth(user: { email: string; created_at: string; is_admin: boolean; username: string | null } | null) {
  setActivePinia(createPinia())
  useAuthStore().user = user
}

describe('AppNavbar shell', () => {
  afterEach(() => {
    document.body.replaceChildren()
  })

  it('renders the Shrt brand as a link to /', async () => {
    await router.push('/manage')
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const wrapper = mount(AppNavbar, { global: globalOptions })
    const brand = wrapper.find('.navbar-brand')
    expect(brand.text()).toBe('Shrt')
    expect(brand.attributes('href')).toBe('/')
  })

  it.each([
    ['/login', 'Log in'],
    ['/new', 'New Link'],
    ['/manage', 'Manage Links'],
    ['/profile', 'Profile'],
    ['/admin', 'User Management'],
  ])('shows the page title for %s', async (path, expectedTitle) => {
    await router.push(path)
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const wrapper = mount(AppNavbar, { global: globalOptions })
    expect(wrapper.find('.navbar-title').text()).toBe(expectedTitle)
  })

  it('calls themeStore.toggle() when the theme button is clicked', async () => {
    await router.push('/manage')
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const themeStore = useThemeStore()
    const toggleSpy = vi.spyOn(themeStore, 'toggle')
    const wrapper = mount(AppNavbar, { global: globalOptions })
    await wrapper.find('.theme-toggle').trigger('click')
    expect(toggleSpy).toHaveBeenCalledTimes(1)
  })

  it('hides the hamburger button when not authenticated', async () => {
    await router.push('/login')
    setAuth(null)
    const wrapper = mount(AppNavbar, { global: globalOptions })
    expect(wrapper.find('.hamburger-btn').exists()).toBe(false)
  })

  it('shows the hamburger button when authenticated', async () => {
    await router.push('/manage')
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const wrapper = mount(AppNavbar, { global: globalOptions })
    expect(wrapper.find('.hamburger-btn').exists()).toBe(true)
  })

  it('renders content passed into the status slot', async () => {
    await router.push('/manage')
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const wrapper = mount(AppNavbar, {
      global: globalOptions,
      slots: { status: '<span class="status-stub" />' },
    })
    expect(wrapper.find('.status-stub').exists()).toBe(true)
  })
})

describe('AppNavbar drawer', () => {
  afterEach(() => {
    document.body.replaceChildren()
  })

  it('is closed by default', async () => {
    await router.push('/manage')
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const wrapper = mount(AppNavbar, { global: globalOptions, attachTo: document.body })
    expect(document.body.querySelector('.drawer-panel')).toBeNull()
    expect(wrapper.find('.hamburger-btn').attributes('aria-expanded')).toBe('false')
    wrapper.unmount()
  })

  it('opens on hamburger click', async () => {
    await router.push('/manage')
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const wrapper = mount(AppNavbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    expect(document.body.querySelector('.drawer-panel')).not.toBeNull()
    expect(wrapper.find('.hamburger-btn').attributes('aria-expanded')).toBe('true')
    wrapper.unmount()
  })

  it('closes on backdrop click', async () => {
    await router.push('/manage')
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const wrapper = mount(AppNavbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    const backdrop = document.body.querySelector('.drawer-backdrop') as HTMLElement
    backdrop.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(document.body.querySelector('.drawer-panel')).toBeNull()
    wrapper.unmount()
  })

  it('closes on Escape key', async () => {
    await router.push('/manage')
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const wrapper = mount(AppNavbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(document.body.querySelector('.drawer-panel')).toBeNull()
    wrapper.unmount()
  })

  it('closes on the close button', async () => {
    await router.push('/manage')
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const wrapper = mount(AppNavbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    const closeBtn = document.body.querySelector('.drawer-close') as HTMLButtonElement
    closeBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(document.body.querySelector('.drawer-panel')).toBeNull()
    wrapper.unmount()
  })

  it('shows the user display name', async () => {
    await router.push('/manage')
    setAuth({ email: 'user@example.com', created_at: '', username: 'testuser', is_admin: false })
    const wrapper = mount(AppNavbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    expect(document.body.querySelector('.drawer-user')?.textContent).toBe('testuser')
    wrapper.unmount()
  })

  it('hides the link to the current page and shows the others, no Admin for non-admin', async () => {
    await router.push('/profile')
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const wrapper = mount(AppNavbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    const text = document.body.querySelector('.drawer-panel')?.textContent ?? ''
    expect(text).toContain('Manage')
    expect(text).toContain('New Link')
    expect(text).not.toContain('Profile')
    expect(text).not.toContain('Admin')
    wrapper.unmount()
  })

  it('shows Admin link for admin users, hidden while already on /admin', async () => {
    await router.push('/admin')
    setAuth({ email: 'admin@example.com', created_at: '', username: 'admin', is_admin: true })
    const wrapper = mount(AppNavbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    const text = document.body.querySelector('.drawer-panel')?.textContent ?? ''
    expect(text).toContain('Manage')
    expect(text).toContain('New Link')
    expect(text).toContain('Profile')
    expect(text).not.toContain('Admin')
    wrapper.unmount()
  })

  it('closes the drawer when a link is clicked', async () => {
    await router.push('/profile')
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const wrapper = mount(AppNavbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    const dashboardLink = document.body.querySelector('.drawer-item') as HTMLAnchorElement
    dashboardLink.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
    await wrapper.vm.$nextTick()
    expect(document.body.querySelector('.drawer-panel')).toBeNull()
    wrapper.unmount()
  })

  it('signs out and redirects to /login', async () => {
    await router.push('/manage')
    setAuth({ email: 'user@example.com', created_at: '', username: 'user', is_admin: false })
    const authStore = useAuthStore()
    const logoutSpy = vi.spyOn(authStore, 'logout').mockResolvedValue(undefined)
    const wrapper = mount(AppNavbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    const signOutBtn = document.body.querySelector('.drawer-item--danger') as HTMLButtonElement
    signOutBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flushPromises()
    expect(logoutSpy).toHaveBeenCalledTimes(1)
    expect(router.currentRoute.value.path).toBe('/login')
    wrapper.unmount()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun run test:unit -- run src/components/__tests__/AppNavbar.spec.ts`
Expected: FAIL — the drawer still only has one link ("Dashboard"), so `'hides the link to the current page...'` fails on `expect(text).toContain('Manage')` / `'New Link'`, and other assertions expecting two non-Profile/Admin links fail too.

- [ ] **Step 3: Update the drawer links**

In `frontend/src/components/AppNavbar.vue`, the current `<nav class="drawer-links">` block (lines 89-108) reads:

```html
        <nav class="drawer-links">
          <RouterLink
            v-if="route.name !== 'dashboard'"
            class="drawer-item"
            to="/dashboard"
            @click="closeDrawer"
          >Dashboard</RouterLink>
          <RouterLink
            v-if="route.name !== 'profile'"
            class="drawer-item"
            to="/profile"
            @click="closeDrawer"
          >Profile</RouterLink>
          <RouterLink
            v-if="authStore.user?.is_admin && route.name !== 'admin'"
            class="drawer-item"
            to="/admin"
            @click="closeDrawer"
          >Admin</RouterLink>
        </nav>
```

Change it to:

```html
        <nav class="drawer-links">
          <RouterLink
            v-if="route.name !== 'manage'"
            class="drawer-item"
            to="/manage"
            @click="closeDrawer"
          >Manage</RouterLink>
          <RouterLink
            v-if="route.name !== 'new-link'"
            class="drawer-item"
            to="/new"
            @click="closeDrawer"
          >New Link</RouterLink>
          <RouterLink
            v-if="route.name !== 'profile'"
            class="drawer-item"
            to="/profile"
            @click="closeDrawer"
          >Profile</RouterLink>
          <RouterLink
            v-if="authStore.user?.is_admin && route.name !== 'admin'"
            class="drawer-item"
            to="/admin"
            @click="closeDrawer"
          >Admin</RouterLink>
        </nav>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun run test:unit -- run src/components/__tests__/AppNavbar.spec.ts`
Expected: PASS, all tests in the file green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AppNavbar.vue frontend/src/components/__tests__/AppNavbar.spec.ts
git commit -m "$(cat <<'EOF'
Disclosure: Based on Claude Code generated output.

feat(frontend): add Manage and New Link nav entries to AppNavbar

Replaces the single "Dashboard" drawer link with two: "Manage"
(/manage) and "New Link" (/new), each hidden while already on that
page, matching the existing contextual-hiding pattern used for
Profile/Admin.
EOF
)"
```

---

### Task 3: URLCard — rename `qr` emit/button to `share`

**Files:**
- Modify: `frontend/src/components/URLCard.vue`
- Test: `frontend/src/components/__tests__/URLCard.spec.ts`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `URLCard` emits `share: [shortCode: string]` (was `qr`), button has class `.btn-share` (was `.btn-qr`) and label "Share" (was "QR"). Task 5 (`ManageView.vue`) listens for this emit and navigates to the `share` route.

- [ ] **Step 1: Write the failing test**

In `frontend/src/components/__tests__/URLCard.spec.ts`, the current first test (lines 17-21) reads:

```ts
  it('emits qr with the short_code when the QR button is clicked', async () => {
    const wrapper = mount(URLCard, { props: { url: mockURL, baseUrl: 'http://localhost' } })
    await wrapper.get('.btn-qr').trigger('click')
    expect(wrapper.emitted('qr')).toEqual([['abc12345']])
  })
```

Change it to:

```ts
  it('emits share with the short_code when the Share button is clicked', async () => {
    const wrapper = mount(URLCard, { props: { url: mockURL, baseUrl: 'http://localhost' } })
    await wrapper.get('.btn-share').trigger('click')
    expect(wrapper.emitted('share')).toEqual([['abc12345']])
  })
```

(The `urlsApi.qrUrl` tests at the bottom of the file test the QR-image-URL helper itself, which `ShareView` still uses in Task 7 — leave those unchanged.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun run test:unit -- run src/components/__tests__/URLCard.spec.ts`
Expected: FAIL — `wrapper.get('.btn-share')` throws because no element matches `.btn-share` yet (the button is still `.btn-qr`).

- [ ] **Step 3: Rename the emit and button**

In `frontend/src/components/URLCard.vue`, line 6 currently reads:

```ts
const emit = defineEmits<{ delete: [id: number]; stats: [id: number]; qr: [shortCode: string]; edit: [id: number] }>()
```

Change it to:

```ts
const emit = defineEmits<{ delete: [id: number]; stats: [id: number]; share: [shortCode: string]; edit: [id: number] }>()
```

Line 65 currently reads:

```html
      <button class="btn-qr" @click="emit('qr', url.short_code)">QR</button>
```

Change it to:

```html
      <button class="btn-share" @click="emit('share', url.short_code)">Share</button>
```

Lines 158-167 (the shared button style rule) currently read:

```css
.btn-qr,
.btn-stats {
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-accent);
  background: transparent;
  color: var(--color-accent);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-qr:hover,
.btn-stats:hover {
  background: var(--color-border);
}
```

Change it to:

```css
.btn-share,
.btn-stats {
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-accent);
  background: transparent;
  color: var(--color-accent);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-share:hover,
.btn-stats:hover {
  background: var(--color-border);
}
```

Lines 208-214 (the combined focus-visible rule) currently read:

```css
.btn-qr:focus-visible,
.btn-stats:focus-visible,
.btn-delete:focus-visible,
.btn-copy:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

Change it to:

```css
.btn-share:focus-visible,
.btn-stats:focus-visible,
.btn-delete:focus-visible,
.btn-copy:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun run test:unit -- run src/components/__tests__/URLCard.spec.ts`
Expected: PASS, all tests in the file green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/URLCard.vue frontend/src/components/__tests__/URLCard.spec.ts
git commit -m "$(cat <<'EOF'
Disclosure: Based on Claude Code generated output.

refactor(frontend): rename URLCard's qr emit/button to share

The management page's QR modal is being replaced by a dedicated share
page (Task 5/7), so the button that used to open it is relabeled
"Share" and its emit renamed to match. Purely a rename — no new
behavior in this component.
EOF
)"
```

---

### Task 4: CreateURLForm — redirect to the share page on success

**Files:**
- Modify: `frontend/src/components/CreateURLForm.vue`
- Test: `frontend/src/components/__tests__/CreateURLForm.spec.ts`

**Interfaces:**
- Consumes: route name `share` (params: `{ code: string }`) from Task 1.
- Produces: nothing consumed by later tasks (this is a leaf — `NewLinkView` in Task 6 just wraps this component unchanged).

- [ ] **Step 1: Write the failing test**

Replace the full contents of `frontend/src/components/__tests__/CreateURLForm.spec.ts` with:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import CreateURLForm from '../CreateURLForm.vue'
import * as urlsStoreModule from '../../stores/urls'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/links/:code/share', name: 'share', component: { template: '<div />' } },
  ],
})

const globalOptions = { plugins: [router] }

const mockCreatedUrl = {
  id: 1,
  short_code: 'newcode1',
  original_url: 'https://example.com',
  created_at: '',
  click_count: 0,
  has_password: false,
  expires_at: null,
}

describe('CreateURLForm', () => {
  let createSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    createSpy = vi.fn()
    vi.spyOn(urlsStoreModule, 'useURLsStore').mockReturnValue({
      create: createSpy,
    } as unknown as ReturnType<typeof urlsStoreModule.useURLsStore>)
  })

  it('renders URL input and submit button', () => {
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    expect(wrapper.find('#original-url').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').text()).toBe('Create short URL')
  })

  it('shows no error initially', () => {
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('calls store.create with valid URL', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, undefined, undefined)
  })

  it('prepends https:// when protocol missing', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, undefined, undefined)
  })

  it('passes custom code when provided', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#custom-code').setValue('my-link')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith('https://example.com', 'my-link', undefined, undefined)
  })

  it('passes password when provided', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#link-password').setValue('secret')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, 'secret', undefined)
  })

  it('passes expiry date when provided', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#expires-at').setValue('2099-01-01T00:00')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith(
      'https://example.com',
      undefined,
      undefined,
      new Date('2099-01-01T00:00').toISOString(),
    )
  })

  it('navigates to the share page after successful creation', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('share')
    expect(router.currentRoute.value.params.code).toBe('newcode1')
  })

  it('shows error for invalid custom code', async () => {
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#custom-code').setValue('x!')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Custom code')
    expect(createSpy).not.toHaveBeenCalled()
  })

  it('shows error for short password', async () => {
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#link-password').setValue('abc')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Password must be at least 6 characters')
    expect(createSpy).not.toHaveBeenCalled()
  })

  it('shows error on 409 conflict', async () => {
    createSpy.mockRejectedValue({ response: { status: 409 } })
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#custom-code').setValue('taken1')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('already taken')
  })

  it('shows generic error on other failures', async () => {
    createSpy.mockRejectedValue({ response: { status: 500 } })
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Failed to create')
  })

  it('disables submit while loading', async () => {
    let resolve: (value: typeof mockCreatedUrl) => void
    createSpy.mockImplementation(() => new Promise<typeof mockCreatedUrl>((r) => { resolve = r }))
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    const btn = wrapper.find('button[type="submit"]')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    expect(btn.attributes('disabled')).toBeDefined()
    resolve!(mockCreatedUrl)
    await flushPromises()
    expect(btn.attributes('disabled')).toBeUndefined()
  })
})
```

Note: every existing `createSpy.mockResolvedValue(undefined)` is now `mockResolvedValue(mockCreatedUrl)` — the real `urlsStore.create()` always resolves to the created `URLOut`, and the component (Step 3 below) will read `.short_code` off that result to build the redirect, so a mock resolving `undefined` would throw. The old `'clears form fields after successful creation'` test is removed (the component no longer clears fields — it navigates away instead) and replaced by `'navigates to the share page after successful creation'`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun run test:unit -- run src/components/__tests__/CreateURLForm.spec.ts`
Expected: FAIL — `'navigates to the share page after successful creation'` fails because the component doesn't call `router.push` yet (`router.currentRoute.value.name` stays whatever it was before submit, not `'share'`).

- [ ] **Step 3: Redirect to the share page on success**

Replace the full contents of `frontend/src/components/CreateURLForm.vue`'s `<script setup>` block (lines 1-59) with:

```html
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useURLsStore } from '../stores/urls'

const router = useRouter()
const urlsStore = useURLsStore()
const originalUrl = ref('')
const customCode = ref('')
const password = ref('')
const expiresAt = ref('')
const error = ref('')
const loading = ref(false)

async function handleCreate() {
  error.value = ''
  if (originalUrl.value && !/^https?:\/\//i.test(originalUrl.value)) {
    originalUrl.value = 'https://' + originalUrl.value
  }
  try {
    const parsed = new URL(originalUrl.value)
    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
      error.value = 'Only http and https URLs are allowed.'
      return
    }
  } catch {
    error.value = 'Please enter a valid URL.'
    return
  }
  if (customCode.value && !/^[A-Za-z0-9_-]{6,16}$/.test(customCode.value)) {
    error.value = 'Custom code must be 6–16 characters and contain only letters, digits, hyphens, or underscores.'
    return
  }
  if (password.value && password.value.length < 6) {
    error.value = 'Password must be at least 6 characters.'
    return
  }
  loading.value = true
  try {
    const created = await urlsStore.create(
      originalUrl.value,
      customCode.value || undefined,
      password.value || undefined,
      expiresAt.value ? new Date(expiresAt.value).toISOString() : undefined,
    )
    router.push({ name: 'share', params: { code: created.short_code } })
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } }).response?.status
    if (status === 409) {
      error.value = 'Short code already taken.'
    } else {
      error.value = 'Failed to create URL.'
    }
  } finally {
    loading.value = false
  }
}
</script>
```

The template and `<style scoped>` blocks are unchanged — leave them exactly as they are.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun run test:unit -- run src/components/__tests__/CreateURLForm.spec.ts`
Expected: PASS, all tests in the file green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CreateURLForm.vue frontend/src/components/__tests__/CreateURLForm.spec.ts
git commit -m "$(cat <<'EOF'
Disclosure: Based on Claude Code generated output.

feat(frontend): redirect to the share page after creating a link

Instead of resetting the form's local fields after a successful
create, CreateURLForm now navigates to /links/:code/share using the
short_code from the created URL. The old field-reset became dead code
once the component navigates away on success, so it's dropped rather
than kept alongside the redirect.
EOF
)"
```

---

### Task 5: ManageView — split off from DashboardView (list/edit/stats/delete, no create form, no QR dialog)

**Files:**
- Create: `frontend/src/views/ManageView.vue`
- Create: `frontend/src/views/__tests__/ManageView.spec.ts`
- Delete: `frontend/src/views/DashboardView.vue`
- Delete: `frontend/src/views/__tests__/DashboardView.spec.ts`

**Interfaces:**
- Consumes: `URLCard`'s `share` emit (Task 3); route name `share` (Task 1) for the share-button navigation.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/views/__tests__/ManageView.spec.ts` with:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useURLsStore } from '../../stores/urls'
import ManageView from '../ManageView.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/login', component: { template: '<div />' } },
    { path: '/links/:code/share', name: 'share', component: { template: '<div />' } },
  ],
})

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

HTMLDialogElement.prototype.showModal = vi.fn()
HTMLDialogElement.prototype.close = vi.fn()

vi.mock('../../api/urls', () => ({
  urlsApi: {
    list: vi.fn().mockResolvedValue([]),
    qrUrl: vi.fn((code: string) => `/api/urls/${code}/qr`),
    remove: vi.fn().mockResolvedValue(undefined),
    update: vi.fn(),
    stats: vi.fn(),
    create: vi.fn(),
  },
}))

vi.mock('../../api/auth', () => ({
  authApi: {
    logout: vi.fn().mockResolvedValue(undefined),
    me: vi.fn(),
    updateUsername: vi.fn(),
  },
}))

const NetworkStatusStub = defineComponent({
  name: 'NetworkStatusIndicator',
  template: '<span class="network-status-stub" />',
})

const AppNavbarStub = defineComponent({
  name: 'AppNavbar',
  template: '<div class="navbar-stub"><slot name="status" /></div>',
})

const URLCardStub = defineComponent({
  name: 'URLCard',
  props: ['url', 'baseUrl'],
  emits: ['share', 'stats', 'delete', 'edit'],
  template: `
    <div class="url-card-stub" :data-id="url.id">
      <button class="stub-share" @click="$emit('share', url.short_code)">Share</button>
      <button class="stub-stats" @click="$emit('stats', url.id)">Stats</button>
      <button class="stub-delete" @click="$emit('delete', url.id)">Delete</button>
      <button class="stub-edit" @click="$emit('edit', url.id)">Edit</button>
    </div>
  `,
})

const globalOptions = {
  plugins: [router],
  stubs: {
    AppNavbar: AppNavbarStub,
    NetworkStatusIndicator: NetworkStatusStub,
    URLCard: URLCardStub,
  },
}

const mockUrl = {
  id: 1,
  short_code: 'abc123',
  original_url: 'https://example.com',
  created_at: '2024-01-01T00:00:00Z',
  click_count: 5,
  has_password: false,
  expires_at: null,
}

const mockStats = {
  url_id: 1,
  short_code: 'abc123',
  original_url: 'https://example.com',
  total_clicks: 5,
  clicks_by_date: { '2024-01-01': 5 },
}

function setupStores(user = { email: 'user@example.com', username: 'testuser', is_admin: false, created_at: '' }) {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  useAuthStore().user = user
  return useURLsStore()
}

describe('ManageView navbar', () => {
  it('renders AppNavbar with the network status indicator in its status slot', async () => {
    const store = setupStores()
    vi.spyOn(store, 'fetchAll').mockResolvedValue(undefined)
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.find('.navbar-stub').exists()).toBe(true)
    expect(wrapper.find('.network-status-stub').exists()).toBe(true)
  })
})

describe('ManageView URL list', () => {
  it('shows empty state when no URLs', async () => {
    const store = setupStores()
    vi.spyOn(store, 'fetchAll').mockResolvedValue(undefined)
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.find('.empty').exists()).toBe(true)
  })

  it('renders a URLCard for each URL', async () => {
    const store = setupStores()
    const mockUrl2 = { ...mockUrl, id: 2, short_code: 'xyz' }
    vi.spyOn(store, 'fetchAll').mockImplementation(async () => {
      store.urls = [mockUrl, mockUrl2]
    })
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.findAll('.url-card-stub')).toHaveLength(2)
  })

  it('shows loadError when fetchAll fails', async () => {
    const store = setupStores()
    vi.spyOn(store, 'fetchAll').mockRejectedValue(new Error('network'))
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Failed to load URLs')
  })
})

describe('ManageView delete flow', () => {
  let store: ReturnType<typeof useURLsStore>

  beforeEach(() => {
    store = setupStores()
    vi.spyOn(store, 'fetchAll').mockImplementation(async () => {
      store.urls = [mockUrl]
    })
  })

  it('opens confirm dialog when URLCard emits delete', async () => {
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-delete').trigger('click')
    await flushPromises()
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled()
    expect(wrapper.find('.confirm-dialog').exists()).toBe(true)
  })

  it('calls urlsStore.remove on confirm', async () => {
    vi.spyOn(store, 'remove').mockResolvedValue(undefined)
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-delete').trigger('click')
    await flushPromises()
    await wrapper.find('.btn-confirm-delete').trigger('click')
    await flushPromises()
    expect(store.remove).toHaveBeenCalledWith(1)
  })

  it('cancels delete without calling remove', async () => {
    vi.spyOn(store, 'remove').mockResolvedValue(undefined)
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-delete').trigger('click')
    await flushPromises()
    await wrapper.find('.confirm-dialog .btn-cancel').trigger('click')
    await flushPromises()
    expect(store.remove).not.toHaveBeenCalled()
  })

  it('shows deleteError when remove fails', async () => {
    vi.spyOn(store, 'remove').mockRejectedValue(new Error('server error'))
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-delete').trigger('click')
    await flushPromises()
    await wrapper.find('.btn-confirm-delete').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Failed to delete')
  })
})

describe('ManageView stats flow', () => {
  let store: ReturnType<typeof useURLsStore>

  beforeEach(() => {
    store = setupStores()
    vi.spyOn(store, 'fetchAll').mockImplementation(async () => {
      store.urls = [mockUrl]
    })
  })

  it('shows stats panel when URLCard emits stats', async () => {
    vi.spyOn(store, 'fetchStats').mockImplementation(async () => {
      store.currentStats = mockStats
    })
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-stats').trigger('click')
    await flushPromises()
    expect(wrapper.find('.stats-panel').exists()).toBe(true)
    expect(wrapper.find('.stats-panel').text()).toContain('abc123')
    expect(wrapper.find('.stats-panel').text()).toContain('5')
  })

  it('closes stats panel on Close click', async () => {
    vi.spyOn(store, 'fetchStats').mockImplementation(async () => {
      store.currentStats = mockStats
    })
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-stats').trigger('click')
    await flushPromises()
    await wrapper.find('.stats-panel button').trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.stats-panel').exists()).toBe(false)
  })

  it('shows statsError when fetchStats fails', async () => {
    vi.spyOn(store, 'fetchStats').mockRejectedValue(new Error('fail'))
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-stats').trigger('click')
    await flushPromises()
    expect(wrapper.find('.stats-panel').exists()).toBe(false)
    expect(wrapper.html()).toContain('Failed to load stats')
  })
})

describe('ManageView share flow', () => {
  let store: ReturnType<typeof useURLsStore>

  beforeEach(() => {
    store = setupStores()
    vi.spyOn(store, 'fetchAll').mockImplementation(async () => {
      store.urls = [mockUrl]
    })
  })

  it('navigates to the share page when URLCard emits share', async () => {
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-share').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('share')
    expect(router.currentRoute.value.params.code).toBe('abc123')
  })
})

describe('ManageView edit flow', () => {
  let store: ReturnType<typeof useURLsStore>

  beforeEach(() => {
    store = setupStores()
    vi.spyOn(store, 'fetchAll').mockImplementation(async () => {
      store.urls = [mockUrl]
    })
  })

  it('opens edit dialog when URLCard emits edit', async () => {
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-edit').trigger('click')
    await flushPromises()
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled()
    expect(wrapper.find('.edit-dialog').exists()).toBe(true)
  })

  it('pre-fills short code from URL', async () => {
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-edit').trigger('click')
    await flushPromises()
    const inputs = wrapper.findAll('.edit-dialog input')
    const shortCodeInput = inputs.find(i => (i.element as HTMLInputElement).value === 'abc123')
    expect(shortCodeInput).toBeDefined()
  })

  it('calls urlsStore.update on save', async () => {
    vi.spyOn(store, 'update').mockResolvedValue({ ...mockUrl })
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-edit').trigger('click')
    await flushPromises()
    await wrapper.find('.edit-dialog form').trigger('submit')
    await flushPromises()
    expect(store.update).toHaveBeenCalledWith(1, expect.objectContaining({ short_code: 'abc123' }))
    expect(wrapper.find('.edit-dialog [role="alert"]').exists()).toBe(false)
  })

  it('shows editError when update fails', async () => {
    vi.spyOn(store, 'update').mockRejectedValue(new Error('conflict'))
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-edit').trigger('click')
    await flushPromises()
    await wrapper.find('.edit-dialog form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('.edit-dialog [role="alert"]').text()).toContain('Failed to update')
  })

  it('cancels edit without calling update', async () => {
    vi.spyOn(store, 'update').mockResolvedValue({ ...mockUrl })
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-edit').trigger('click')
    await flushPromises()
    await wrapper.find('.edit-dialog .btn-cancel').trigger('click')
    await wrapper.vm.$nextTick()
    expect(store.update).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun run test:unit -- run src/views/__tests__/ManageView.spec.ts`
Expected: FAIL — `../ManageView.vue` doesn't exist yet.

- [ ] **Step 3: Create ManageView.vue and delete DashboardView.vue**

Create `frontend/src/views/ManageView.vue` with:

```html
<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useURLsStore } from '../stores/urls'
import URLCard from '../components/URLCard.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'
import AppNavbar from '../components/AppNavbar.vue'
import type { StatsOut, URLOut } from '../api/urls'
const BASE_URL = window.location.origin

const router = useRouter()
const urlsStore = useURLsStore()
const selectedStats = ref<StatsOut | null>(null)
const statsError = ref('')
const deleteError = ref('')
const loadError = ref('')
const pendingDeleteId = ref<number | null>(null)
const dialogRef = ref<HTMLDialogElement | null>(null)
const editDialogRef = ref<HTMLDialogElement | null>(null)
const editingUrl = ref<URLOut | null>(null)
const editShortCode = ref('')
const editPassword = ref('')
const editRemovePassword = ref(false)
const editExpiresAt = ref('')
const editError = ref('')

onMounted(() => {
  loadError.value = ''
  urlsStore.fetchAll().catch(() => {
    loadError.value = 'Failed to load URLs. Please refresh.'
  })
})

watch(pendingDeleteId, (id) => {
  if (id !== null) {
    nextTick(() => dialogRef.value?.showModal())
  } else {
    dialogRef.value?.close()
  }
})

function handleShare(shortCode: string) {
  router.push({ name: 'share', params: { code: shortCode } })
}

watch(editingUrl, (url) => {
  if (url !== null) {
    nextTick(() => editDialogRef.value?.showModal())
  } else {
    editDialogRef.value?.close()
  }
})

function handleEdit(id: number) {
  const url = urlsStore.urls.find(u => u.id === id) ?? null
  if (!url) return
  editingUrl.value = url
  editShortCode.value = url.short_code
  editPassword.value = ''
  editRemovePassword.value = false
  editExpiresAt.value = url.expires_at ? url.expires_at.slice(0, 16) : ''
  editError.value = ''
}

function cancelEdit() {
  editingUrl.value = null
}

async function confirmEdit() {
  if (!editingUrl.value) return
  editError.value = ''
  try {
    const payload: Parameters<typeof urlsStore.update>[1] = { short_code: editShortCode.value }
    if (editRemovePassword.value) payload.remove_password = true
    else if (editPassword.value) payload.password = editPassword.value
    payload.expires_at = editExpiresAt.value ? new Date(editExpiresAt.value).toISOString() : null
    await urlsStore.update(editingUrl.value.id, payload)
    editingUrl.value = null
  } catch {
    editError.value = 'Failed to update link. Check the short code is unique.'
  }
}

async function handleStats(id: number) {
  statsError.value = ''
  try {
    await urlsStore.fetchStats(id)
    selectedStats.value = urlsStore.currentStats
  } catch {
    statsError.value = 'Failed to load stats'
  }
}

function handleDelete(id: number) {
  pendingDeleteId.value = id
}

async function confirmDelete() {
  if (pendingDeleteId.value === null) return
  const id = pendingDeleteId.value
  pendingDeleteId.value = null
  deleteError.value = ''
  try {
    await urlsStore.remove(id)
    if (selectedStats.value?.url_id === id) selectedStats.value = null
  } catch {
    deleteError.value = 'Failed to delete URL. Please try again.'
  }
}

function cancelDelete() {
  pendingDeleteId.value = null
}
</script>

<template>
  <div class="dashboard">
    <AppNavbar>
      <template #status>
        <NetworkStatusIndicator />
      </template>
    </AppNavbar>
    <main class="dash-content">
      <section>
        <h2>Your URLs</h2>
        <p v-if="urlsStore.urls.length === 0" class="empty">No URLs yet. Create one on the New Link page.</p>
        <URLCard
          v-for="url in urlsStore.urls"
          :key="url.id"
          :url="url"
          :base-url="BASE_URL"
          @share="handleShare"
          @edit="handleEdit"
          @stats="handleStats"
          @delete="handleDelete"
        />
      </section>
      <aside v-if="selectedStats" class="stats-panel">
        <h3>Stats for /{{ selectedStats.short_code }}</h3>
        <p><strong>Total clicks:</strong> {{ selectedStats.total_clicks }}</p>
        <table v-if="Object.keys(selectedStats.clicks_by_date).length">
          <thead><tr><th>Date</th><th>Clicks</th></tr></thead>
          <tbody>
            <tr v-for="(count, date) in selectedStats.clicks_by_date" :key="date">
              <td>{{ date }}</td><td>{{ count }}</td>
            </tr>
          </tbody>
        </table>
        <button @click="selectedStats = null">Close</button>
      </aside>
      <p v-if="loadError" class="error" role="alert">{{ loadError }}</p>
      <p v-if="statsError" class="error">{{ statsError }}</p>
      <p v-if="deleteError" class="error" role="alert">{{ deleteError }}</p>
    </main>

    <dialog
      ref="dialogRef"
      class="confirm-dialog"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      aria-describedby="confirm-desc"
      @close="cancelDelete"
    >
      <h3 id="confirm-title">Delete URL</h3>
      <p id="confirm-desc">Are you sure you want to delete this short URL? This cannot be undone.</p>
      <div class="confirm-actions">
        <button class="btn-cancel" autofocus @click="cancelDelete">Cancel</button>
        <button class="btn-confirm-delete" @click="confirmDelete">Delete</button>
      </div>
    </dialog>

    <dialog
      ref="editDialogRef"
      class="edit-dialog"
      aria-modal="true"
      aria-labelledby="edit-title"
      @close="cancelEdit"
    >
      <h3 id="edit-title">Edit Link</h3>
      <form @submit.prevent="confirmEdit">
        <label>
          Short code
          <input v-model="editShortCode" minlength="3" maxlength="16" pattern="[a-zA-Z0-9_-]+" required autofocus />
        </label>
        <label>
          New password <span class="field-hint">(leave empty to keep current)</span>
          <input v-model="editPassword" type="password" autocomplete="new-password" :disabled="editRemovePassword" />
        </label>
        <label v-if="editingUrl?.has_password" class="checkbox-label">
          <input v-model="editRemovePassword" type="checkbox" />
          Remove password
        </label>
        <label>
          Expires at <span class="field-hint">(leave empty for no expiry)</span>
          <input v-model="editExpiresAt" type="datetime-local" />
        </label>
        <p v-if="editError" class="error" role="alert">{{ editError }}</p>
        <div class="confirm-actions">
          <button type="button" class="btn-cancel" @click="cancelEdit">Cancel</button>
          <button type="submit" class="btn-save">Save</button>
        </div>
      </form>
    </dialog>
  </div>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: var(--color-background);
}

.dash-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.empty {
  color: var(--color-text);
  opacity: 0.6;
}

.stats-panel {
  background: var(--color-background-soft);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-top: 2rem;
  transition: background 0.35s ease;
}

.stats-panel table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}

.stats-panel th,
.stats-panel td {
  text-align: left;
  padding: 0.5rem;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
}

.error {
  color: var(--color-error);
}

.confirm-dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  padding: 1.5rem;
  max-width: 380px;
  width: 90%;
  z-index: 200;
}

.confirm-dialog h3 {
  margin: 0 0 0.5rem;
  color: var(--color-heading);
}

.confirm-dialog p {
  margin: 0 0 1.25rem;
  color: var(--color-text);
  font-size: 0.9rem;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-cancel {
  padding: 0.4rem 1rem;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  color: var(--color-text);
  transition: background 0.2s;
}

.btn-cancel:hover {
  background: var(--color-border);
}

.btn-confirm-delete {
  padding: 0.4rem 1rem;
  border: 1px solid var(--color-error);
  background: var(--color-error);
  color: var(--color-background);
  border-radius: 4px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-confirm-delete:hover {
  opacity: 0.85;
}

.edit-dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  padding: 1.5rem;
  max-width: 420px;
  width: 90%;
  z-index: 200;
}

.edit-dialog h3 {
  margin: 0 0 1rem;
  color: var(--color-heading);
}

.edit-dialog label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: var(--color-text);
  margin-bottom: 0.75rem;
}

.edit-dialog input[type="text"],
.edit-dialog input[type="password"],
.edit-dialog input[type="datetime-local"] {
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  font-size: 0.875rem;
}

.edit-dialog input:focus {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

.checkbox-label {
  flex-direction: row !important;
  align-items: center;
  gap: 0.5rem !important;
}

.field-hint {
  font-size: 0.75rem;
  opacity: 0.6;
  font-weight: normal;
}

.btn-save {
  padding: 0.4rem 1rem;
  border: 1px solid var(--color-accent);
  background: var(--color-accent);
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-save:hover {
  opacity: 0.85;
}
</style>
```

This is `DashboardView.vue` with: the `CreateURLForm` import and `<CreateURLForm />` usage removed; `qrShortCode`, `qrDialogRef`, `qrSrc`, the `watch(qrShortCode, ...)`, `handleQr`, and `closeQr` removed; the whole `<dialog class="qr-dialog">` block and all of its CSS (`.qr-dialog`, `.qr-target`, `.qr-image`, `.qr-actions`, `.btn-qr-download`, and the combined `.btn-qr-download:focus-visible, .qr-actions .btn-cancel:focus-visible` rule) removed; `urlsApi` import replaced with a type-only `import type { StatsOut, URLOut } from '../api/urls'` (it was only used for `qrUrl`); `useRouter`/`router` added; `@qr="handleQr"` on `URLCard` replaced with `@share="handleShare"`; and the empty-state copy updated from "Create one above." to "Create one on the New Link page." (accurate now that the create form isn't on this page).

Then delete the old files:

```bash
git rm frontend/src/views/DashboardView.vue frontend/src/views/__tests__/DashboardView.spec.ts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun run test:unit -- run src/views/__tests__/ManageView.spec.ts`
Expected: PASS, all tests in the file green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/ManageView.vue frontend/src/views/__tests__/ManageView.spec.ts
git commit -m "$(cat <<'EOF'
Disclosure: Based on Claude Code generated output.

refactor(frontend): split ManageView out of DashboardView

DashboardView.vue is renamed to ManageView.vue: the create form moves
to NewLinkView.vue (Task 6) and the QR dialog is dropped in favor of
the new Share button/page (Task 3/7). Everything else (list, edit,
stats, delete) is unchanged.
EOF
)"
```

---

### Task 6: NewLinkView — dedicated create-link page

**Files:**
- Create: `frontend/src/views/NewLinkView.vue`
- Create: `frontend/src/views/__tests__/NewLinkView.spec.ts`

**Interfaces:**
- Consumes: `AppNavbar` and `CreateURLForm`, both unchanged by this task (`CreateURLForm`'s redirect from Task 4 is what navigates the user away from this page after a successful create).
- Produces: nothing consumed by later tasks. Route `new-link` (Task 1) points here.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/views/__tests__/NewLinkView.spec.ts`:

```ts
import { describe, it, expect, vi } from 'vitest'
import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import NewLinkView from '../NewLinkView.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/login', component: { template: '<div />' } },
  ],
})

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

vi.mock('../../api/auth', () => ({
  authApi: {
    logout: vi.fn().mockResolvedValue(undefined),
    me: vi.fn(),
    updateUsername: vi.fn(),
  },
}))

const NetworkStatusStub = defineComponent({
  name: 'NetworkStatusIndicator',
  template: '<span class="network-status-stub" />',
})

const AppNavbarStub = defineComponent({
  name: 'AppNavbar',
  template: '<div class="navbar-stub"><slot name="status" /></div>',
})

const CreateURLFormStub = defineComponent({
  name: 'CreateURLForm',
  template: '<div class="create-url-form-stub" />',
})

const globalOptions = {
  plugins: [router],
  stubs: {
    AppNavbar: AppNavbarStub,
    NetworkStatusIndicator: NetworkStatusStub,
    CreateURLForm: CreateURLFormStub,
  },
}

function setupStores() {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  useAuthStore().user = { email: 'user@example.com', username: 'testuser', is_admin: false, created_at: '' }
}

describe('NewLinkView', () => {
  it('renders AppNavbar with the network status indicator in its status slot', () => {
    setupStores()
    const wrapper = mount(NewLinkView, { global: globalOptions })
    expect(wrapper.find('.navbar-stub').exists()).toBe(true)
    expect(wrapper.find('.network-status-stub').exists()).toBe(true)
  })

  it('renders CreateURLForm', () => {
    setupStores()
    const wrapper = mount(NewLinkView, { global: globalOptions })
    expect(wrapper.find('.create-url-form-stub').exists()).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun run test:unit -- run src/views/__tests__/NewLinkView.spec.ts`
Expected: FAIL — `Failed to resolve import "../NewLinkView.vue"` (the file doesn't exist yet).

- [ ] **Step 3: Create NewLinkView.vue**

Create `frontend/src/views/NewLinkView.vue`:

```vue
<script setup lang="ts">
import AppNavbar from '../components/AppNavbar.vue'
import CreateURLForm from '../components/CreateURLForm.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'
</script>

<template>
  <div class="new-link">
    <AppNavbar>
      <template #status>
        <NetworkStatusIndicator />
      </template>
    </AppNavbar>
    <main class="new-link-content">
      <CreateURLForm />
    </main>
  </div>
</template>

<style scoped>
.new-link {
  min-height: 100vh;
  background: var(--color-background);
}

.new-link-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1rem;
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun run test:unit -- run src/views/__tests__/NewLinkView.spec.ts`
Expected: PASS, all tests in the file green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/NewLinkView.vue frontend/src/views/__tests__/NewLinkView.spec.ts
git commit -m "$(cat <<'EOF'
Disclosure: Based on Claude Code generated output.

feat(frontend): add NewLinkView as the dedicated create-link page

Small wrapper around AppNavbar and the existing CreateURLForm. Route
new-link (Task 1) points here; CreateURLForm's own redirect (Task 4)
is what takes the user to the share page after a successful create.
EOF
)"
```

---

### Task 7: ShareView — copy/QR/share page for a single link

**Files:**
- Create: `frontend/src/views/ShareView.vue`
- Create: `frontend/src/views/__tests__/ShareView.spec.ts`

**Interfaces:**
- Consumes: route name `share` (Task 1) for `route.params.code`; `urlsStore.urls` / `urlsStore.fetchAll()` (unchanged, same client-side lookup pattern `ManageView`'s `handleEdit` already uses); `urlsApi.qrUrl` (unchanged); route name `manage` (Task 1) for the "Back to Manage" link.
- Produces: nothing consumed by later tasks. This is the last task — `CreateURLForm` (Task 4) and `ManageView`'s share button (Task 3/5) both navigate here.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/views/__tests__/ShareView.spec.ts`:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useURLsStore } from '../../stores/urls'
import ShareView from '../ShareView.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/manage', name: 'manage', component: { template: '<div />' } },
    { path: '/links/:code/share', name: 'share', component: { template: '<div />' } },
  ],
})

vi.mock('../../api/urls', () => ({
  urlsApi: {
    list: vi.fn().mockResolvedValue([]),
    qrUrl: vi.fn((code: string) => `/api/urls/${code}/qr`),
  },
}))

const NetworkStatusStub = defineComponent({
  name: 'NetworkStatusIndicator',
  template: '<span class="network-status-stub" />',
})

const AppNavbarStub = defineComponent({
  name: 'AppNavbar',
  template: '<div class="navbar-stub"><slot name="status" /></div>',
})

const globalOptions = {
  plugins: [router],
  stubs: {
    AppNavbar: AppNavbarStub,
    NetworkStatusIndicator: NetworkStatusStub,
  },
}

const mockUrl = {
  id: 1,
  short_code: 'abc123',
  original_url: 'https://example.com',
  created_at: '2024-01-01T00:00:00Z',
  click_count: 5,
  has_password: false,
  expires_at: null,
}

function setupStore() {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  return useURLsStore()
}

describe('ShareView', () => {
  beforeEach(async () => {
    await router.push('/links/abc123/share')
  })

  afterEach(() => {
    // @ts-expect-error jsdom does not define navigator.share by default
    delete navigator.share
  })

  it('renders the short URL and a copy button when the link is found', async () => {
    const store = setupStore()
    store.urls = [mockUrl]
    const wrapper = mount(ShareView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.text()).toContain(`${window.location.origin}/abc123`)
    expect(wrapper.find('.btn-copy').exists()).toBe(true)
  })

  it('calls the clipboard API when the copy button is clicked', async () => {
    const store = setupStore()
    store.urls = [mockUrl]
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const wrapper = mount(ShareView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.btn-copy').trigger('click')
    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/abc123`)
  })

  it('renders the QR image with the correct src', async () => {
    const store = setupStore()
    store.urls = [mockUrl]
    const wrapper = mount(ShareView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.find('.qr-image').attributes('src')).toBe('/api/urls/abc123/qr')
  })

  it('renders the native share button when navigator.share is defined', async () => {
    const store = setupStore()
    store.urls = [mockUrl]
    Object.defineProperty(navigator, 'share', { value: vi.fn().mockResolvedValue(undefined), configurable: true })
    const wrapper = mount(ShareView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.find('.btn-share-native').exists()).toBe(true)
  })

  it('does not render the native share button when navigator.share is undefined', async () => {
    const store = setupStore()
    store.urls = [mockUrl]
    const wrapper = mount(ShareView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.find('.btn-share-native').exists()).toBe(false)
  })

  it('renders social share links with the correct href', async () => {
    const store = setupStore()
    store.urls = [mockUrl]
    const wrapper = mount(ShareView, { global: globalOptions })
    await flushPromises()
    const shortUrl = `${window.location.origin}/abc123`
    expect(wrapper.find('.btn-twitter').attributes('href')).toBe(`https://twitter.com/intent/tweet?url=${encodeURIComponent(shortUrl)}`)
    expect(wrapper.find('.btn-whatsapp').attributes('href')).toBe(`https://wa.me/?text=${encodeURIComponent(shortUrl)}`)
  })

  it('shows a not-found message when the code does not match any URL', async () => {
    const store = setupStore()
    store.urls = [mockUrl]
    await router.push('/links/doesnotexist/share')
    const wrapper = mount(ShareView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.find('.not-found').exists()).toBe(true)
    expect(wrapper.find('.not-found').text()).toContain('not found')
  })

  it('calls fetchAll on mount when the store is empty', async () => {
    const store = setupStore()
    const fetchAllSpy = vi.spyOn(store, 'fetchAll').mockImplementation(async () => {
      store.urls = [mockUrl]
    })
    mount(ShareView, { global: globalOptions })
    await flushPromises()
    expect(fetchAllSpy).toHaveBeenCalled()
  })

  it('skips fetchAll on mount when the store is already populated', async () => {
    const store = setupStore()
    store.urls = [mockUrl]
    const fetchAllSpy = vi.spyOn(store, 'fetchAll')
    mount(ShareView, { global: globalOptions })
    await flushPromises()
    expect(fetchAllSpy).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun run test:unit -- run src/views/__tests__/ShareView.spec.ts`
Expected: FAIL — `Failed to resolve import "../ShareView.vue"` (the file doesn't exist yet).

- [ ] **Step 3: Create ShareView.vue**

Create `frontend/src/views/ShareView.vue`:

```vue
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useURLsStore } from '../stores/urls'
import { urlsApi } from '../api/urls'
import AppNavbar from '../components/AppNavbar.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'

const BASE_URL = window.location.origin

const route = useRoute()
const urlsStore = useURLsStore()
const loadError = ref('')
const copied = ref(false)
const copyError = ref(false)
const canShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function'

const shortCode = computed(() => route.params.code as string)
const url = computed(() => urlsStore.urls.find(u => u.short_code === shortCode.value) ?? null)
const shortUrl = computed(() => `${BASE_URL}/${shortCode.value}`)
const qrSrc = computed(() => urlsApi.qrUrl(shortCode.value))
const twitterHref = computed(() => `https://twitter.com/intent/tweet?url=${encodeURIComponent(shortUrl.value)}`)
const whatsappHref = computed(() => `https://wa.me/?text=${encodeURIComponent(shortUrl.value)}`)

onMounted(async () => {
  if (urlsStore.urls.length === 0) {
    try {
      await urlsStore.fetchAll()
    } catch {
      loadError.value = 'Failed to load link data. Please refresh.'
    }
  }
})

async function copyShortUrl() {
  copyError.value = false
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(shortUrl.value)
    } else {
      const el = document.createElement('textarea')
      el.value = shortUrl.value
      el.style.cssText = 'position:fixed;opacity:0'
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch {
    copyError.value = true
    setTimeout(() => { copyError.value = false }, 1500)
  }
}

async function nativeShare() {
  try {
    await navigator.share({ title: 'Shrt', url: shortUrl.value })
  } catch {
    // user cancelled the native share sheet — no action needed
  }
}
</script>

<template>
  <div class="share">
    <AppNavbar>
      <template #status>
        <NetworkStatusIndicator />
      </template>
    </AppNavbar>
    <main class="share-content">
      <template v-if="url">
        <h2>Your short link is ready</h2>
        <div class="short-url-row">
          <code>{{ shortUrl }}</code>
          <button class="btn-copy" :class="{ 'btn-copy--error': copyError }" @click="copyShortUrl">{{ copied ? 'Copied!' : copyError ? 'Failed!' : 'Copy' }}</button>
        </div>
        <img :src="qrSrc" class="qr-image" :alt="`QR code for ${shortUrl}`" width="256" height="256" />
        <div class="share-actions">
          <button v-if="canShare" class="btn-share-native" @click="nativeShare">Share…</button>
          <a class="btn-social btn-twitter" :href="twitterHref" target="_blank" rel="noopener noreferrer">Share on X</a>
          <a class="btn-social btn-whatsapp" :href="whatsappHref" target="_blank" rel="noopener noreferrer">Share on WhatsApp</a>
        </div>
        <RouterLink class="back-link" :to="{ name: 'manage' }">Back to Manage</RouterLink>
      </template>
      <template v-else>
        <p class="not-found">Link not found.</p>
        <RouterLink class="back-link" :to="{ name: 'manage' }">Back to Manage</RouterLink>
      </template>
      <p v-if="loadError" class="error" role="alert">{{ loadError }}</p>
    </main>
  </div>
</template>

<style scoped>
.share {
  min-height: 100vh;
  background: var(--color-background);
}

.share-content {
  max-width: 480px;
  margin: 0 auto;
  padding: 2rem 1rem;
  text-align: center;
}

.short-url-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin: 1rem 0;
}

.short-url-row code {
  font-size: 0.95rem;
  color: var(--color-code);
  word-break: break-all;
}

.btn-copy {
  font-size: 0.8rem;
  padding: 0.3rem 0.7rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  cursor: pointer;
  background: transparent;
  color: var(--color-text);
  transition: background 0.2s;
}

.btn-copy:hover {
  background: var(--color-border);
}

.btn-copy--error {
  border-color: var(--color-error);
  color: var(--color-error);
}

.qr-image {
  display: block;
  width: 256px;
  height: 256px;
  max-width: 100%;
  margin: 0 auto 1.5rem;
  background: #fff;
  padding: 0.5rem;
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.share-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.btn-share-native,
.btn-social {
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-accent);
  background: var(--color-accent);
  color: var(--color-background);
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
  font-size: 0.9rem;
  transition: opacity 0.2s;
}

.btn-share-native:hover,
.btn-social:hover {
  opacity: 0.85;
}

.btn-share-native:focus-visible,
.btn-social:focus-visible,
.btn-copy:focus-visible,
.back-link:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.back-link {
  display: inline-block;
  margin-top: 0.5rem;
  color: var(--color-link);
}

.not-found {
  color: var(--color-text);
  margin-bottom: 1rem;
}

.error {
  color: var(--color-error);
  margin-top: 1rem;
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun run test:unit -- run src/views/__tests__/ShareView.spec.ts`
Expected: PASS, all tests in the file green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/ShareView.vue frontend/src/views/__tests__/ShareView.spec.ts
git commit -m "$(cat <<'EOF'
Disclosure: Based on Claude Code generated output.

feat(frontend): add ShareView for copy/QR/social sharing of a link

Reads route.params.code, fetching the URL list first only if the
store is empty (covers direct navigation/refresh — there's no
single-link GET endpoint, so this mirrors the client-side lookup
ManageView's edit flow already uses). Renders the short URL with a
copy button, the existing QR endpoint as an image, a native share
button (feature-detected, no polyfill), and plain-link X/WhatsApp
share buttons. Shows a "Link not found" state with a link back to
/manage when the code doesn't match anything in the store.
EOF
)"
```

---

## Post-Implementation

After Task 7's commit, run the full frontend verification one more time from the worktree root to confirm nothing regressed across the whole change set:

```bash
cd frontend && bun run test:unit -- run && bun run type-check && bun run lint && bun run build
```

No backend changes in this plan, so no backend test run is needed.

Then push the branch and open a PR against `develop`, following this repo's established workflow (worktree → PR → review → merge).
