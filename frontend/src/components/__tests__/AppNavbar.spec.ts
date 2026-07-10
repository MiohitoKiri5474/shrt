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
