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
