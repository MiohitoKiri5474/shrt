# Shared Navbar Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the duplicated header/dropdown markup in `DashboardView`, `AdminView`, `ProfileView`, and `LoginView` with one shared `Navbar.vue` component (brand left, page title center, theme toggle + hamburger right) whose hamburger opens a real side drawer instead of the old anchored dropdown.

**Architecture:** A single self-contained `frontend/src/components/Navbar.vue` reads `useRoute()`, `useAuthStore()`, and `useThemeStore()` directly — no required props. Each of the four views drops its own header markup and mounts `<Navbar>` instead; `DashboardView` additionally projects `NetworkStatusIndicator` into Navbar's `status` slot.

**Tech Stack:** Vue 3 `<script setup>`, Pinia, Vue Router, Vitest + `@vue/test-utils`, bun.

## Global Constraints

- Frontend package manager is `bun` (`bun run <script>`), not `npm`/`yarn`.
- Test command: `bun run test:unit -- run <path>` (Vitest). Full suite: `bun run test:unit -- run`.
- Type-check: `bun run type-check` (runs `vue-tsc --build`). Lint: `bun run lint`.
- `route.meta` types as `Record<PropertyKey, unknown>` (confirmed in `vue-router`'s shipped types) — no module augmentation needed; read custom meta fields with an `as` cast, matching existing usage of `to.meta.requiresAuth`/`to.meta.requiresAdmin` in `frontend/src/router/index.ts`.
- Teleported content (`<Teleport to="body">`) is not found by `wrapper.find(...)` — query it via `document.body.querySelector(...)` after mounting with `attachTo: document.body`, and clean up with `document.body.replaceChildren()` in `afterEach`. This matches the existing pattern in `frontend/src/components/__tests__/NetworkStatusIndicator.spec.ts`.
- Scope is exactly 4 views: `DashboardView`, `AdminView`, `ProfileView`, `LoginView`. `PasswordGateView` and `ExpiredView` are out of scope — do not touch them.
- Spec doc: `docs/superpowers/specs/2026-07-08-shared-navbar-design.md` — refer back to it if a task's intent is unclear.

---

### Task 1: Route titles

**Files:**
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Produces: each in-scope route's `meta.title: string`, consumed by `Navbar.vue` in Task 2 via `route.meta.title`.

- [ ] **Step 1: Add `meta.title` to the four in-scope routes**

In `frontend/src/router/index.ts`, change the `routes` array so it reads exactly:

```ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/dashboard' },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { title: 'Log in' },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { requiresAuth: true, title: 'Dashboard' },
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
  if (!auth.isAuthenticated && to.name !== 'login') {
    await auth.restore()
  }
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return '/login'
  }
  if (to.meta.requiresAdmin && !auth.user?.is_admin) {
    return '/dashboard'
  }
})

export default router
```

(Only the `meta` object on each of the four in-scope route records changes; the redirect, `/p/:code`, `/expired`, and `router.beforeEach` are untouched.)

- [ ] **Step 2: Write a failing test asserting the titles**

Create `frontend/src/router/__tests__/index.spec.ts`:

```ts
import { describe, it, expect } from 'vitest'
import router from '../index'

describe('router meta titles', () => {
  it.each([
    ['/login', 'Log in'],
    ['/dashboard', 'Dashboard'],
    ['/profile', 'Profile'],
    ['/admin', 'User Management'],
  ])('sets meta.title for %s', (path, expectedTitle) => {
    const match = router.resolve(path)
    expect(match.meta.title).toBe(expectedTitle)
  })
})
```

- [ ] **Step 3: Run the test**

Run: `bun run test:unit -- run src/router/__tests__/index.spec.ts`
Expected (before Step 1 is applied): if run first, FAILs with title `undefined` not matching. If Step 1 was already applied above, this PASSes immediately — that's fine, Steps 1 and 2 together form the red/green cycle; run once after both to confirm.

- [ ] **Step 4: Confirm PASS**

Run: `bun run test:unit -- run src/router/__tests__/index.spec.ts`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/router/index.ts src/router/__tests__/index.spec.ts
git commit -m "feat(frontend): add page titles to route meta"
```

---

### Task 2: Navbar shell (brand, title, theme toggle, hamburger visibility, status slot)

**Files:**
- Create: `frontend/src/components/Navbar.vue`
- Create: `frontend/src/components/__tests__/Navbar.spec.ts`

**Interfaces:**
- Consumes: `useAuthStore()` (`isAuthenticated: ComputedRef<boolean>`, `user: Ref<UserOut | null>` where `UserOut = { email: string, username: string | null, is_admin: boolean }`), `useThemeStore()` (`isDark: Ref<boolean>`, `toggle(): void`), `useRoute()` (`route.meta.title: unknown`).
- Produces: `Navbar` component, no props, named slot `status`. Root markup exposes `.navbar-brand` (link to `/`), `.navbar-title` (renders `route.meta.title`), `.theme-toggle` (button), `.hamburger-btn` (button, only rendered when `authStore.isAuthenticated` is `true`). This task does not yet render the drawer body — `.hamburger-btn` click only needs to exist and be clickable; drawer behavior is Task 3.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/__tests__/Navbar.spec.ts`:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useThemeStore } from '../../stores/theme'
import Navbar from '../Navbar.vue'

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
    { path: '/dashboard', name: 'dashboard', component: { template: '<div />' }, meta: { title: 'Dashboard' } },
    { path: '/profile', name: 'profile', component: { template: '<div />' }, meta: { title: 'Profile' } },
    { path: '/admin', name: 'admin', component: { template: '<div />' }, meta: { title: 'User Management' } },
  ],
})

const globalOptions = { plugins: [router] }

function setAuth(user: { email: string; username: string | null; is_admin: boolean } | null) {
  setActivePinia(createPinia())
  useAuthStore().user = user
}

describe('Navbar shell', () => {
  afterEach(() => {
    document.body.replaceChildren()
  })

  it('renders the Shrt brand as a link to /', async () => {
    await router.push('/dashboard')
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const wrapper = mount(Navbar, { global: globalOptions })
    const brand = wrapper.find('.navbar-brand')
    expect(brand.text()).toBe('Shrt')
    expect(brand.attributes('href')).toBe('/')
  })

  it.each([
    ['/login', 'Log in'],
    ['/dashboard', 'Dashboard'],
    ['/profile', 'Profile'],
    ['/admin', 'User Management'],
  ])('shows the page title for %s', async (path, expectedTitle) => {
    await router.push(path)
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const wrapper = mount(Navbar, { global: globalOptions })
    expect(wrapper.find('.navbar-title').text()).toBe(expectedTitle)
  })

  it('calls themeStore.toggle() when the theme button is clicked', async () => {
    await router.push('/dashboard')
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const themeStore = useThemeStore()
    const toggleSpy = vi.spyOn(themeStore, 'toggle')
    const wrapper = mount(Navbar, { global: globalOptions })
    await wrapper.find('.theme-toggle').trigger('click')
    expect(toggleSpy).toHaveBeenCalledTimes(1)
  })

  it('hides the hamburger button when not authenticated', async () => {
    await router.push('/login')
    setAuth(null)
    const wrapper = mount(Navbar, { global: globalOptions })
    expect(wrapper.find('.hamburger-btn').exists()).toBe(false)
  })

  it('shows the hamburger button when authenticated', async () => {
    await router.push('/dashboard')
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const wrapper = mount(Navbar, { global: globalOptions })
    expect(wrapper.find('.hamburger-btn').exists()).toBe(true)
  })

  it('renders content passed into the status slot', async () => {
    await router.push('/dashboard')
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const wrapper = mount(Navbar, {
      global: globalOptions,
      slots: { status: '<span class="status-stub" />' },
    })
    expect(wrapper.find('.status-stub').exists()).toBe(true)
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `bun run test:unit -- run src/components/__tests__/Navbar.spec.ts`
Expected: FAIL — `Cannot find module '../Navbar.vue'` (component doesn't exist yet).

- [ ] **Step 3: Create the Navbar shell**

Create `frontend/src/components/Navbar.vue`:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'

const route = useRoute()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const pageTitle = computed(() => (route.meta.title as string | undefined) ?? '')
</script>

<template>
  <header class="navbar">
    <RouterLink to="/" class="navbar-brand">Shrt</RouterLink>
    <h1 class="navbar-title">{{ pageTitle }}</h1>
    <div class="navbar-actions">
      <slot name="status" />
      <button
        class="theme-toggle"
        :aria-label="themeStore.isDark ? '昼モードに切り替え' : '夜モードに切り替え'"
        :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
        @click="themeStore.toggle()"
      >
        <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
      </button>
      <button
        v-if="authStore.isAuthenticated"
        class="hamburger-btn"
        aria-haspopup="dialog"
        aria-label="Open menu"
      >
        <span class="bar" />
        <span class="bar" />
        <span class="bar" />
      </button>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0.75rem 2rem;
  background: var(--color-background-soft);
  border-bottom: 1px solid var(--color-border);
  transition: background 0.35s ease, border-color 0.35s ease;
}

.navbar-brand {
  justify-self: start;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--color-heading);
  letter-spacing: 0.02em;
  text-decoration: none;
}

.navbar-title {
  justify-self: center;
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading);
}

.navbar-actions {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.theme-toggle {
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, border-color 0.2s, transform 0.2s;
  color: var(--color-text);
  padding: 0;
}

.theme-toggle:hover {
  background: var(--color-border);
  transform: rotate(15deg);
}

.theme-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.hamburger-btn {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  width: 2.1rem;
  height: 2.1rem;
  padding: 0.35rem;
  background: transparent;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.hamburger-btn:hover {
  background: var(--color-border);
}

.hamburger-btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.bar {
  display: block;
  width: 100%;
  height: 2px;
  background: var(--color-text);
  border-radius: 2px;
}
</style>
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `bun run test:unit -- run src/components/__tests__/Navbar.spec.ts`
Expected: `9 passed` (1 brand + 4 title cases + 1 theme toggle + 1 hidden + 1 shown + 1 slot)

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/components/Navbar.vue src/components/__tests__/Navbar.spec.ts
git commit -m "feat(frontend): add Navbar shell component"
```

---

### Task 3: Navbar side drawer

**Files:**
- Modify: `frontend/src/components/Navbar.vue`
- Modify: `frontend/src/components/__tests__/Navbar.spec.ts`

**Interfaces:**
- Consumes: `useRouter()` (added in this task, for the sign-out redirect), everything from Task 2.
- Produces: clicking `.hamburger-btn` toggles a teleported (`to="body"`) `.drawer-backdrop` > `.drawer-panel` (`role="dialog" aria-modal="true"`). Panel contains `.drawer-user` (text), `.drawer-item` links (`Dashboard`/`Profile`/`Admin` — each hidden when `route.name` matches the link's own route, `Admin` also hidden unless `authStore.user?.is_admin`), and `.drawer-item--danger` (Sign out button). Closes via backdrop click, `Esc`, `.drawer-close` button, or clicking any `.drawer-item`.

- [ ] **Step 1: Write the failing tests**

Append to `frontend/src/components/__tests__/Navbar.spec.ts` (add this `describe` block after the existing `describe('Navbar shell', ...)` block, keeping all existing imports/setup):

```ts
describe('Navbar drawer', () => {
  afterEach(() => {
    document.body.replaceChildren()
  })

  it('is closed by default', async () => {
    await router.push('/dashboard')
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const wrapper = mount(Navbar, { global: globalOptions, attachTo: document.body })
    expect(document.body.querySelector('.drawer-panel')).toBeNull()
    expect(wrapper.find('.hamburger-btn').attributes('aria-expanded')).toBe('false')
    wrapper.unmount()
  })

  it('opens on hamburger click', async () => {
    await router.push('/dashboard')
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const wrapper = mount(Navbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    expect(document.body.querySelector('.drawer-panel')).not.toBeNull()
    expect(wrapper.find('.hamburger-btn').attributes('aria-expanded')).toBe('true')
    wrapper.unmount()
  })

  it('closes on backdrop click', async () => {
    await router.push('/dashboard')
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const wrapper = mount(Navbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    const backdrop = document.body.querySelector('.drawer-backdrop') as HTMLElement
    backdrop.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(document.body.querySelector('.drawer-panel')).toBeNull()
    wrapper.unmount()
  })

  it('closes on Escape key', async () => {
    await router.push('/dashboard')
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const wrapper = mount(Navbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(document.body.querySelector('.drawer-panel')).toBeNull()
    wrapper.unmount()
  })

  it('closes on the close button', async () => {
    await router.push('/dashboard')
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const wrapper = mount(Navbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    const closeBtn = document.body.querySelector('.drawer-close') as HTMLButtonElement
    closeBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(document.body.querySelector('.drawer-panel')).toBeNull()
    wrapper.unmount()
  })

  it('shows the user display name', async () => {
    await router.push('/dashboard')
    setAuth({ email: 'user@example.com', username: 'testuser', is_admin: false })
    const wrapper = mount(Navbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    expect(document.body.querySelector('.drawer-user')?.textContent).toBe('testuser')
    wrapper.unmount()
  })

  it('hides the link to the current page and shows the others, no Admin for non-admin', async () => {
    await router.push('/profile')
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const wrapper = mount(Navbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    const text = document.body.querySelector('.drawer-panel')?.textContent ?? ''
    expect(text).toContain('Dashboard')
    expect(text).not.toContain('Profile')
    expect(text).not.toContain('Admin')
    wrapper.unmount()
  })

  it('shows Admin link for admin users, hidden while already on /admin', async () => {
    await router.push('/admin')
    setAuth({ email: 'admin@example.com', username: 'admin', is_admin: true })
    const wrapper = mount(Navbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    const text = document.body.querySelector('.drawer-panel')?.textContent ?? ''
    expect(text).toContain('Dashboard')
    expect(text).toContain('Profile')
    expect(text).not.toContain('Admin')
    wrapper.unmount()
  })

  it('closes the drawer when a link is clicked', async () => {
    await router.push('/profile')
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const wrapper = mount(Navbar, { global: globalOptions, attachTo: document.body })
    await wrapper.find('.hamburger-btn').trigger('click')
    const dashboardLink = document.body.querySelector('.drawer-item') as HTMLAnchorElement
    dashboardLink.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
    await wrapper.vm.$nextTick()
    expect(document.body.querySelector('.drawer-panel')).toBeNull()
    wrapper.unmount()
  })

  it('signs out and redirects to /login', async () => {
    await router.push('/dashboard')
    setAuth({ email: 'user@example.com', username: 'user', is_admin: false })
    const authStore = useAuthStore()
    const logoutSpy = vi.spyOn(authStore, 'logout').mockResolvedValue(undefined)
    const wrapper = mount(Navbar, { global: globalOptions, attachTo: document.body })
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

- [ ] **Step 2: Run the tests to verify they fail**

Run: `bun run test:unit -- run src/components/__tests__/Navbar.spec.ts`
Expected: the new `Navbar drawer` tests FAIL (no `.drawer-panel`/`aria-expanded` ever rendered yet); the `Navbar shell` tests from Task 2 still PASS.

- [ ] **Step 3: Add the drawer to Navbar.vue**

Replace the full contents of `frontend/src/components/Navbar.vue` with:

```vue
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const pageTitle = computed(() => (route.meta.title as string | undefined) ?? '')
const showDrawer = ref(false)

function openDrawer() {
  showDrawer.value = true
}

function closeDrawer() {
  showDrawer.value = false
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') closeDrawer()
}

watch(showDrawer, (open) => {
  if (open) {
    document.addEventListener('keydown', handleKeydown)
  } else {
    document.removeEventListener('keydown', handleKeydown)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
})

async function handleSignOut() {
  closeDrawer()
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <header class="navbar">
    <RouterLink to="/" class="navbar-brand">Shrt</RouterLink>
    <h1 class="navbar-title">{{ pageTitle }}</h1>
    <div class="navbar-actions">
      <slot name="status" />
      <button
        class="theme-toggle"
        :aria-label="themeStore.isDark ? '昼モードに切り替え' : '夜モードに切り替え'"
        :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
        @click="themeStore.toggle()"
      >
        <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
      </button>
      <button
        v-if="authStore.isAuthenticated"
        class="hamburger-btn"
        :aria-expanded="showDrawer"
        aria-haspopup="dialog"
        :aria-label="showDrawer ? 'Close menu' : 'Open menu'"
        @click="openDrawer"
      >
        <span class="bar" />
        <span class="bar" />
        <span class="bar" />
      </button>
    </div>
  </header>

  <Teleport to="body">
    <div v-if="showDrawer" class="drawer-backdrop" @click="closeDrawer">
      <aside
        class="drawer-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Navigation menu"
        @click.stop
      >
        <div class="drawer-header">
          <span class="drawer-user">{{ authStore.user?.username ?? authStore.user?.email }}</span>
          <button class="drawer-close" aria-label="Close menu" @click="closeDrawer">✕</button>
        </div>
        <hr class="drawer-sep" />
        <nav class="drawer-links">
          <RouterLink
            v-if="route.name !== 'dashboard'"
            class="drawer-item"
            to="/dashboard"
            role="menuitem"
            @click="closeDrawer"
          >Dashboard</RouterLink>
          <RouterLink
            v-if="route.name !== 'profile'"
            class="drawer-item"
            to="/profile"
            role="menuitem"
            @click="closeDrawer"
          >Profile</RouterLink>
          <RouterLink
            v-if="authStore.user?.is_admin && route.name !== 'admin'"
            class="drawer-item"
            to="/admin"
            role="menuitem"
            @click="closeDrawer"
          >Admin</RouterLink>
        </nav>
        <hr class="drawer-sep" />
        <button class="drawer-item drawer-item--danger" role="menuitem" @click="handleSignOut">Sign out</button>
      </aside>
    </div>
  </Teleport>
</template>

<style scoped>
.navbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0.75rem 2rem;
  background: var(--color-background-soft);
  border-bottom: 1px solid var(--color-border);
  transition: background 0.35s ease, border-color 0.35s ease;
}

.navbar-brand {
  justify-self: start;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--color-heading);
  letter-spacing: 0.02em;
  text-decoration: none;
}

.navbar-title {
  justify-self: center;
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading);
}

.navbar-actions {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.theme-toggle {
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, border-color 0.2s, transform 0.2s;
  color: var(--color-text);
  padding: 0;
}

.theme-toggle:hover {
  background: var(--color-border);
  transform: rotate(15deg);
}

.theme-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.hamburger-btn {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  width: 2.1rem;
  height: 2.1rem;
  padding: 0.35rem;
  background: transparent;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.hamburger-btn:hover {
  background: var(--color-border);
}

.hamburger-btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.bar {
  display: block;
  width: 100%;
  height: 2px;
  background: var(--color-text);
  border-radius: 2px;
}

.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 200;
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: min(300px, 85vw);
  height: 100%;
  background: var(--color-background-soft);
  border-left: 1px solid var(--color-border);
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  padding: 1rem;
  animation: drawer-slide-in 0.2s ease-out;
}

@keyframes drawer-slide-in {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .drawer-panel {
    animation: none;
  }
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.drawer-user {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  opacity: 0.85;
  font-weight: 500;
  color: var(--color-text);
}

.drawer-close {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  color: var(--color-text);
  padding: 0.25rem;
}

.drawer-close:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.drawer-sep {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: 0.75rem 0;
}

.drawer-links {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.drawer-item {
  display: block;
  width: 100%;
  padding: 0.6rem 0.75rem;
  font-size: 0.9rem;
  color: var(--color-text);
  text-decoration: none;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
}

.drawer-item:hover {
  background: var(--color-background-mute);
}

.drawer-item:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}

.drawer-item--danger {
  color: var(--color-error);
}
</style>
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `bun run test:unit -- run src/components/__tests__/Navbar.spec.ts`
Expected: all tests in both `describe` blocks PASS (19 total: 9 shell + 10 drawer).

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/components/Navbar.vue src/components/__tests__/Navbar.spec.ts
git commit -m "feat(frontend): add side drawer to Navbar"
```

---

### Task 4: Migrate DashboardView to Navbar

**Files:**
- Modify: `frontend/src/views/DashboardView.vue`
- Modify: `frontend/src/views/__tests__/DashboardView.spec.ts`

**Interfaces:**
- Consumes: `Navbar` (Task 3), with `status` slot.

- [ ] **Step 1: Remove the old header and dead state from DashboardView.vue**

In `frontend/src/views/DashboardView.vue`, change the imports at the top from:

```ts
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useURLsStore } from '../stores/urls'
import { useThemeStore } from '../stores/theme'
import CreateURLForm from '../components/CreateURLForm.vue'
import URLCard from '../components/URLCard.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'
import { urlsApi, type StatsOut, type URLOut } from '../api/urls'
const BASE_URL = window.location.origin

const router = useRouter()
const authStore = useAuthStore()
const urlsStore = useURLsStore()
const themeStore = useThemeStore()
const selectedStats = ref<StatsOut | null>(null)
const statsError = ref('')
const deleteError = ref('')
const loadError = ref('')
const showMenu = ref(false)
const menuRef = ref<HTMLDivElement | null>(null)
const pendingDeleteId = ref<number | null>(null)
```

to:

```ts
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useURLsStore } from '../stores/urls'
import CreateURLForm from '../components/CreateURLForm.vue'
import URLCard from '../components/URLCard.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'
import Navbar from '../components/Navbar.vue'
import { urlsApi, type StatsOut, type URLOut } from '../api/urls'
const BASE_URL = window.location.origin

const urlsStore = useURLsStore()
const selectedStats = ref<StatsOut | null>(null)
const statsError = ref('')
const deleteError = ref('')
const loadError = ref('')
const pendingDeleteId = ref<number | null>(null)
```

Then remove the `handleOutsideClick` function entirely:

```ts
function handleOutsideClick(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    showMenu.value = false
  }
}
```

Then change:

```ts
onMounted(() => {
  loadError.value = ''
  urlsStore.fetchAll().catch(() => {
    loadError.value = 'Failed to load URLs. Please refresh.'
  })
  document.addEventListener('click', handleOutsideClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleOutsideClick)
})
```

to:

```ts
onMounted(() => {
  loadError.value = ''
  urlsStore.fetchAll().catch(() => {
    loadError.value = 'Failed to load URLs. Please refresh.'
  })
})
```

Then remove the `handleLogout` function entirely:

```ts
async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
```

Then replace the header block in the `<template>`:

```html
    <header class="dash-header">
      <h1>Shrt</h1>
      <nav class="dash-nav">
        <NetworkStatusIndicator />
        <button
          class="theme-toggle"
          :aria-label="themeStore.isDark ? '昼モードに切り替え' : '夜モードに切り替え'"
          :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
          @click="themeStore.toggle()"
        >
          <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
        </button>
        <div ref="menuRef" class="hamburger-wrapper">
          <button
            class="hamburger-btn"
            :aria-expanded="showMenu"
            aria-haspopup="true"
            :aria-label="showMenu ? 'Close menu' : 'Open menu'"
            @keydown.esc.prevent="showMenu = false"
            @click.stop="showMenu = !showMenu"
          >
            <span class="bar" />
            <span class="bar" />
            <span class="bar" />
          </button>
          <div v-if="showMenu" class="dropdown-menu" role="menu" @keydown.esc.prevent="showMenu = false">
            <div class="dropdown-user">
              <span class="user-display">{{ authStore.user?.username ?? authStore.user?.email }}</span>
            </div>
            <hr class="dropdown-sep" />
            <RouterLink
              class="dropdown-item"
              to="/profile"
              role="menuitem"
              @click="showMenu = false"
            >Profile</RouterLink>
            <RouterLink
              v-if="authStore.user?.is_admin"
              class="dropdown-item"
              to="/admin"
              role="menuitem"
              @click="showMenu = false"
            >Admin</RouterLink>
            <hr v-if="authStore.user?.is_admin" class="dropdown-sep" />
            <button class="dropdown-item dropdown-item--danger" role="menuitem" @click="handleLogout">Sign out</button>
          </div>
        </div>
      </nav>
    </header>
```

with:

```html
    <Navbar>
      <template #status>
        <NetworkStatusIndicator />
      </template>
    </Navbar>
```

Then delete these now-unused style rules from the `<style scoped>` block: `.dash-header`, `.dash-header h1`, `.dash-nav`, `.theme-toggle` and all its variants (`:hover`, `:focus-visible`), `.hamburger-wrapper`, `.hamburger-btn` and all its variants, `.bar`, `.dropdown-menu`, `.dropdown-user`, `.dropdown-sep`, `.dropdown-item` and all its variants, `.user-display`. Leave `.dashboard`, `.dash-content`, and everything from `.empty` onward untouched.

- [ ] **Step 2: Update DashboardView.spec.ts**

In `frontend/src/views/__tests__/DashboardView.spec.ts`, add a `Navbar` stub next to the other stubs. Change:

```ts
const NetworkStatusStub = defineComponent({
  name: 'NetworkStatusIndicator',
  template: '<span class="network-status-stub" />',
})
```

to:

```ts
const NetworkStatusStub = defineComponent({
  name: 'NetworkStatusIndicator',
  template: '<span class="network-status-stub" />',
})

const NavbarStub = defineComponent({
  name: 'Navbar',
  template: '<div class="navbar-stub"><slot name="status" /></div>',
})
```

and change:

```ts
const globalOptions = {
  plugins: [router],
  stubs: {
    NetworkStatusIndicator: NetworkStatusStub,
    CreateURLForm: CreateURLFormStub,
    URLCard: URLCardStub,
  },
}
```

to:

```ts
const globalOptions = {
  plugins: [router],
  stubs: {
    Navbar: NavbarStub,
    NetworkStatusIndicator: NetworkStatusStub,
    CreateURLForm: CreateURLFormStub,
    URLCard: URLCardStub,
  },
}
```

Then delete the entire `describe('DashboardView hamburger menu', ...)` block (the one with `is closed by default`, `opens on hamburger button click`, etc. — 8 tests), the entire `describe('DashboardView logout', ...)` block, and the entire `describe('DashboardView profile link', ...)` block. In their place, add:

```ts
describe('DashboardView navbar', () => {
  it('renders Navbar with the network status indicator in its status slot', async () => {
    const store = setupStores()
    vi.spyOn(store, 'fetchAll').mockResolvedValue(undefined)
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.find('.navbar-stub').exists()).toBe(true)
    expect(wrapper.find('.network-status-stub').exists()).toBe(true)
  })
})
```

The `describe('DashboardView URL list', ...)`, `describe('DashboardView delete flow', ...)`, `describe('DashboardView stats flow', ...)`, `describe('DashboardView QR flow', ...)`, and `describe('DashboardView edit flow', ...)` blocks are untouched.

- [ ] **Step 3: Run DashboardView tests**

Run: `bun run test:unit -- run src/views/__tests__/DashboardView.spec.ts`
Expected: all tests PASS (the 8 removed hamburger tests + 1 logout test + 1 profile-link test are replaced by the 1 new navbar test; net test count in this file drops by 9).

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/views/DashboardView.vue src/views/__tests__/DashboardView.spec.ts
git commit -m "refactor(frontend): migrate DashboardView to shared Navbar"
```

---

### Task 5: Migrate AdminView to Navbar

**Files:**
- Modify: `frontend/src/views/AdminView.vue`
- Modify: `frontend/src/views/__tests__/AdminView.spec.ts`

**Interfaces:**
- Consumes: `Navbar` (Task 3), no slot content (Admin page passes nothing into `status`).

- [ ] **Step 1: Remove the old header and dead state from AdminView.vue**

In `frontend/src/views/AdminView.vue`, change:

```ts
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useAdminStore } from '../stores/admin'
import { useThemeStore } from '../stores/theme'
import AddUserForm from '../components/AddUserForm.vue'

const authStore = useAuthStore()
const adminStore = useAdminStore()
const themeStore = useThemeStore()

const showAddUserModal = ref(false)
const showMenu = ref(false)
const successMessage = ref('')
const loadError = ref('')
const deleteError = ref('')
const roleError = ref('')
const pendingDeleteId = ref<number | null>(null)
const dialogRef = ref<HTMLDialogElement | null>(null)
const menuRef = ref<HTMLDivElement | null>(null)

onMounted(() => {
  loadError.value = ''
  adminStore.fetchAll().catch(() => {
    loadError.value = 'Failed to load users. Please refresh.'
  })
  document.addEventListener('click', handleOutsideClick)
})
```

to:

```ts
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useAdminStore } from '../stores/admin'
import AddUserForm from '../components/AddUserForm.vue'
import Navbar from '../components/Navbar.vue'

const authStore = useAuthStore()
const adminStore = useAdminStore()

const showAddUserModal = ref(false)
const successMessage = ref('')
const loadError = ref('')
const deleteError = ref('')
const roleError = ref('')
const pendingDeleteId = ref<number | null>(null)
const dialogRef = ref<HTMLDialogElement | null>(null)

onMounted(() => {
  loadError.value = ''
  adminStore.fetchAll().catch(() => {
    loadError.value = 'Failed to load users. Please refresh.'
  })
})
```

Then remove the `handleOutsideClick` function entirely:

```ts
function handleOutsideClick(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    showMenu.value = false
  }
}
```

Then change:

```ts
onBeforeUnmount(() => {
  if (successTimer) clearTimeout(successTimer)
  document.removeEventListener('click', handleOutsideClick)
})
```

to:

```ts
onBeforeUnmount(() => {
  if (successTimer) clearTimeout(successTimer)
})
```

Then replace the header block in the `<template>`:

```html
    <header class="admin-header">
      <h1>User Management</h1>
      <nav class="admin-nav">
        <button
          class="theme-toggle"
          :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
          @click="themeStore.toggle()"
        >
          <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
        </button>
        <div ref="menuRef" class="hamburger-wrapper">
          <button
            class="hamburger-btn"
            :aria-expanded="showMenu"
            aria-haspopup="true"
            :aria-label="showMenu ? 'Close menu' : 'Open menu'"
            @keydown.esc.prevent="showMenu = false"
            @click.stop="showMenu = !showMenu"
          >
            <span class="bar" />
            <span class="bar" />
            <span class="bar" />
          </button>
          <div v-if="showMenu" class="dropdown-menu" role="menu" @keydown.esc.prevent="showMenu = false">
            <RouterLink
              class="dropdown-item"
              to="/dashboard"
              role="menuitem"
              @click="showMenu = false"
            >
              ← Dashboard
            </RouterLink>
          </div>
        </div>
      </nav>
    </header>
```

with:

```html
    <Navbar />
```

Then delete these now-unused style rules from the `<style scoped>` block: `.admin-header`, `.admin-header h1`, `.admin-nav`, `.hamburger-wrapper`, `.hamburger-btn` and all its variants, `.bar`, `.dropdown-menu`, `.dropdown-item` and all its variants, `.theme-toggle` and all its variants. Leave `.admin`, `.admin-content`, and everything from `.content-header` onward untouched.

- [ ] **Step 2: Update AdminView.spec.ts**

In `frontend/src/views/__tests__/AdminView.spec.ts`, add a `Navbar` stub. Change:

```ts
// Stub AddUserForm so it doesn't attach document listeners during AdminView tests
const AddUserFormStub = defineComponent({
  name: 'AddUserForm',
  emits: ['close', 'user-added'],
  template: '<div class="add-user-form-stub" />',
})

const globalOptions = {
  stubs: {
    RouterLink: true,
    AddUserForm: AddUserFormStub,
  },
}
```

to:

```ts
// Stub AddUserForm so it doesn't attach document listeners during AdminView tests
const AddUserFormStub = defineComponent({
  name: 'AddUserForm',
  emits: ['close', 'user-added'],
  template: '<div class="add-user-form-stub" />',
})

const NavbarStub = defineComponent({
  name: 'Navbar',
  template: '<div class="navbar-stub" />',
})

const globalOptions = {
  stubs: {
    RouterLink: true,
    AddUserForm: AddUserFormStub,
    Navbar: NavbarStub,
  },
}
```

Then delete the entire `describe('hamburger menu', ...)` block. In its place, add:

```ts
it('renders Navbar', async () => {
  const wrapper = mount(AdminView, { global: globalOptions })
  await flushPromises()
  expect(wrapper.find('.navbar-stub').exists()).toBe(true)
})
```

(add this as a top-level `it` inside the outer `describe('AdminView', ...)` block, alongside the existing `it('shows the Add User button...')` etc.)

All other blocks (`toast behaviour`, `handleUserAdded closes modal...`, `role toggle`) are untouched.

- [ ] **Step 3: Run AdminView tests**

Run: `bun run test:unit -- run src/views/__tests__/AdminView.spec.ts`
Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/views/AdminView.vue src/views/__tests__/AdminView.spec.ts
git commit -m "refactor(frontend): migrate AdminView to shared Navbar"
```

---

### Task 6: Migrate ProfileView to Navbar

**Files:**
- Modify: `frontend/src/views/ProfileView.vue`
- Modify: `frontend/src/views/__tests__/ProfileView.spec.ts`

**Interfaces:**
- Consumes: `Navbar` (Task 3), no slot content.

- [ ] **Step 1: Remove the old header and dead state from ProfileView.vue**

In `frontend/src/views/ProfileView.vue`, change:

```ts
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'

const authStore = useAuthStore()
const themeStore = useThemeStore()

const showMenu = ref(false)
const menuRef = ref<HTMLDivElement | null>(null)

function handleOutsideClick(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    showMenu.value = false
  }
}

onMounted(() => document.addEventListener('click', handleOutsideClick))
onBeforeUnmount(() => document.removeEventListener('click', handleOutsideClick))

function extractStatus(e: unknown): number | undefined {
```

to:

```ts
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import Navbar from '../components/Navbar.vue'

const authStore = useAuthStore()

function extractStatus(e: unknown): number | undefined {
```

Then replace the header block in the `<template>`:

```html
    <header class="profile-header">
      <h1>Profile</h1>
      <nav class="profile-nav">
        <button
          class="theme-toggle"
          :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
          @click="themeStore.toggle()"
        >
          <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
        </button>
        <div ref="menuRef" class="hamburger-wrapper">
          <button
            class="hamburger-btn"
            :aria-expanded="showMenu"
            aria-haspopup="true"
            :aria-label="showMenu ? 'Close menu' : 'Open menu'"
            @keydown.esc.prevent="showMenu = false"
            @click.stop="showMenu = !showMenu"
          >
            <span class="bar" />
            <span class="bar" />
            <span class="bar" />
          </button>
          <div v-if="showMenu" class="dropdown-menu" role="menu" @keydown.esc.prevent="showMenu = false">
            <RouterLink
              class="dropdown-item"
              to="/dashboard"
              role="menuitem"
              @click="showMenu = false"
            >
              ← Dashboard
            </RouterLink>
          </div>
        </div>
      </nav>
    </header>
```

with:

```html
    <Navbar />
```

Then delete these now-unused style rules from the `<style scoped>` block: `.profile-header`, `.profile-header h1`, `.profile-nav`, `.hamburger-wrapper`, `.hamburger-btn` and all its variants, `.bar`, `.dropdown-menu`, `.dropdown-item` and all its variants, `.theme-toggle` and all its variants. Leave `.profile` and `.profile-content` onward untouched.

- [ ] **Step 2: Update ProfileView.spec.ts**

In `frontend/src/views/__tests__/ProfileView.spec.ts`, add a `Navbar` stub. Change the imports at the top:

```ts
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import ProfileView from '../ProfileView.vue'
```

to:

```ts
import { describe, it, expect, vi } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import ProfileView from '../ProfileView.vue'
```

Change:

```ts
const globalOptions = { plugins: [router] }
```

to:

```ts
const NavbarStub = defineComponent({
  name: 'Navbar',
  template: '<div class="navbar-stub" />',
})

const globalOptions = { plugins: [router], stubs: { Navbar: NavbarStub } }
```

Then delete the entire `describe('ProfileView navigation', ...)` block (the one with `'has a back-to-dashboard link in the hamburger menu'`). In its place, add:

```ts
describe('ProfileView navbar', () => {
  it('renders Navbar', async () => {
    setupStore()
    const wrapper = mount(ProfileView, { global: globalOptions })
    expect(wrapper.find('.navbar-stub').exists()).toBe(true)
  })
})
```

The `describe('ProfileView username section', ...)`, `describe('ProfileView email section', ...)`, and `describe('ProfileView password section', ...)` blocks are untouched. The `matchMedia` mock at the top of the file becomes unused now that `ProfileView.vue` no longer calls `useThemeStore()` directly — leave it in place; it's harmless dead weight and removing it is out of scope for this task.

- [ ] **Step 3: Run ProfileView tests**

Run: `bun run test:unit -- run src/views/__tests__/ProfileView.spec.ts`
Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/views/ProfileView.vue src/views/__tests__/ProfileView.spec.ts
git commit -m "refactor(frontend): migrate ProfileView to shared Navbar"
```

---

### Task 7: Migrate LoginView to Navbar

**Files:**
- Modify: `frontend/src/views/LoginView.vue`
- Modify: `frontend/src/views/__tests__/LoginView.spec.ts`

**Interfaces:**
- Consumes: `Navbar` (Task 3), no slot content. `Navbar` renders no hamburger here since the mock/real `authStore.isAuthenticated` is `false` pre-login.

- [ ] **Step 1: Remove the old theme toggle and restructure LoginView.vue**

In `frontend/src/views/LoginView.vue`, change:

```ts
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'

const identifier = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
```

to:

```ts
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import Navbar from '../components/Navbar.vue'

const identifier = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const router = useRouter()
const authStore = useAuthStore()
```

Then replace the entire `<template>` block:

```html
<template>
  <div class="login-container">
    <button
      class="theme-toggle"
      :aria-label="themeStore.isDark ? '昼モードに切り替え' : '夜モードに切り替え'"
      :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
      @click="themeStore.toggle()"
    >
      <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
    </button>

    <div class="login-card">
      <h1>Shrt</h1>
      <form @submit.prevent="handleSubmit" data-testid="login-form">
        <div class="field">
          <label for="identifier">Email or Username</label>
          <input id="identifier" v-model="identifier" type="text" required autocomplete="username" />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input id="password" v-model="password" type="password" required autocomplete="current-password" />
        </div>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <p v-if="isOnCooldown" class="cooldown" role="status">
          Too many failed attempts. Please wait {{ cooldownSecondsLeft }}s before trying again.
        </p>
        <button type="submit" :disabled="loading || isOnCooldown">
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>
    </div>
  </div>
</template>
```

with:

```html
<template>
  <div class="login-page">
    <Navbar />
    <div class="login-container">
      <div class="login-card">
        <form @submit.prevent="handleSubmit" data-testid="login-form">
          <div class="field">
            <label for="identifier">Email or Username</label>
            <input id="identifier" v-model="identifier" type="text" required autocomplete="username" />
          </div>
          <div class="field">
            <label for="password">Password</label>
            <input id="password" v-model="password" type="password" required autocomplete="current-password" />
          </div>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <p v-if="isOnCooldown" class="cooldown" role="status">
            Too many failed attempts. Please wait {{ cooldownSecondsLeft }}s before trying again.
          </p>
          <button type="submit" :disabled="loading || isOnCooldown">
            {{ loading ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
```

Then in the `<style scoped>` block, change:

```css
.login-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-background);
  transition: background 0.35s ease;
}

.theme-toggle {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, transform 0.2s;
  color: var(--color-text);
  padding: 0;
}

.theme-toggle:hover {
  background: var(--color-border);
  transform: rotate(15deg);
}

.login-card {
  background: var(--color-background-soft);
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  width: 100%;
  max-width: 400px;
  transition: background 0.35s ease;
}

h1 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
  font-weight: 600;
}
```

to:

```css
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-background);
  transition: background 0.35s ease;
}

.login-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.login-card {
  background: var(--color-background-soft);
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  width: 100%;
  max-width: 400px;
  transition: background 0.35s ease;
}
```

Then change the combined focus-visible selector:

```css
button[type='submit']:focus-visible,
.theme-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

to:

```css
button[type='submit']:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

- [ ] **Step 2: Update LoginView.spec.ts**

In `frontend/src/views/__tests__/LoginView.spec.ts`, add a `Navbar` stub. Change:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import LoginView from '../LoginView.vue'
import * as authStoreModule from '../../stores/auth'
```

to:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import LoginView from '../LoginView.vue'
import * as authStoreModule from '../../stores/auth'
```

Change:

```ts
const globalOptions = { plugins: [router] }
```

to:

```ts
const NavbarStub = defineComponent({
  name: 'Navbar',
  template: '<div class="navbar-stub" />',
})

const globalOptions = { plugins: [router], stubs: { Navbar: NavbarStub } }
```

Then add one new test inside the existing `describe('LoginView', ...)` block, alongside the others (after the `beforeEach`):

```ts
  it('renders Navbar', () => {
    const wrapper = mountLogin()
    expect(wrapper.find('.navbar-stub').exists()).toBe(true)
  })
```

All existing tests in this file are untouched — none of them reference `.theme-toggle`, `h1`, or `.login-container`, so the template restructure in Step 1 doesn't affect them. The `matchMedia` mock at the top of the file becomes unused now that `LoginView.vue` no longer calls `useThemeStore()` directly — leave it in place, same as Task 6.

- [ ] **Step 3: Run LoginView tests**

Run: `bun run test:unit -- run src/views/__tests__/LoginView.spec.ts`
Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/views/LoginView.vue src/views/__tests__/LoginView.spec.ts
git commit -m "refactor(frontend): migrate LoginView to shared Navbar"
```

---

### Task 8: Final verification

**Files:** none (verification only)

**Interfaces:** none

- [ ] **Step 1: Run the full frontend test suite**

Run: `cd frontend && bun run test:unit -- run`
Expected: all test files pass, 0 failures.

- [ ] **Step 2: Type-check**

Run: `cd frontend && bun run type-check`
Expected: no errors.

- [ ] **Step 3: Lint**

Run: `cd frontend && bun run lint`
Expected: no errors (auto-fixable issues are fixed in place by `--fix`; re-run `git status` afterward and include any auto-fixed files in the commit below if the lint step modified anything).

- [ ] **Step 4: Production build**

Run: `cd frontend && bun run build`
Expected: build succeeds (this also re-runs type-check via the `build` script's `run-p type-check "build-only {@}"`).

- [ ] **Step 5: Manual smoke check**

Start the dev server (`cd frontend && bun run dev`), and in a browser:
- Visit `/login`: confirm the navbar shows `Shrt` (left), `Log in` (center), theme toggle (right), no hamburger.
- Log in, land on `/dashboard`: confirm navbar shows `Shrt`, `Dashboard`, the online/offline status dot, theme toggle, hamburger. Click the hamburger — a drawer slides in from the right with your username, a `Profile` link, no `Dashboard` link (you're on it), and `Sign out`. Click outside the drawer (backdrop) — it closes. Open it again and press `Esc` — it closes.
- Navigate to `/profile`: navbar title is `Profile`; drawer has `Dashboard` and no `Profile` link.
- If your test user is an admin, navigate to `/admin`: navbar title is `User Management`; drawer has `Dashboard`, `Profile`, no `Admin` link.
- Toggle dark/light mode from the navbar theme button on at least two of these pages; confirm it applies immediately and persists across navigation.

- [ ] **Step 6: Commit any lint auto-fixes (only if Step 3 changed files)**

```bash
cd frontend
git status --short
# If lint auto-fixed anything:
git add -u
git commit -m "style(frontend): apply lint auto-fixes"
```
