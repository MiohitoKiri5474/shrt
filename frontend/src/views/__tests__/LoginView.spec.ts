import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import LoginView from '../LoginView.vue'
import * as authStoreModule from '../../stores/auth'

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

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/dashboard', component: { template: '<div />' } },
  ],
})

const AppNavbarStub = defineComponent({
  name: 'AppNavbar',
  template: '<div class="navbar-stub" />',
})

const globalOptions = { plugins: [router], stubs: { AppNavbar: AppNavbarStub } }

function mountLogin() {
  return mount(LoginView, { global: globalOptions })
}

describe('LoginView', () => {
  let loginSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    loginSpy = vi.fn()
    vi.spyOn(authStoreModule, 'useAuthStore').mockReturnValue({
      login: loginSpy,
    } as unknown as ReturnType<typeof authStoreModule.useAuthStore>)
  })

  it('renders AppNavbar', () => {
    const wrapper = mountLogin()
    expect(wrapper.find('.navbar-stub').exists()).toBe(true)
  })

  it('renders email and password fields', () => {
    const wrapper = mountLogin()
    expect(wrapper.find('#identifier').exists()).toBe(true)
    expect(wrapper.find('#password').exists()).toBe(true)
  })

  it('renders Sign in button', () => {
    const wrapper = mountLogin()
    expect(wrapper.find('button[type="submit"]').text()).toBe('Sign in')
  })

  it('shows no error initially', () => {
    const wrapper = mountLogin()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('calls authStore.login with entered credentials on submit', async () => {
    loginSpy.mockResolvedValue(undefined)
    const wrapper = mountLogin()
    await wrapper.find('#identifier').setValue('user@example.com')
    await wrapper.find('#password').setValue('secret123')
    await wrapper.find('[data-testid="login-form"]').trigger('submit')
    await flushPromises()
    expect(loginSpy).toHaveBeenCalledWith('user@example.com', 'secret123')
  })

  it('redirects to /dashboard on successful login', async () => {
    loginSpy.mockResolvedValue(undefined)
    const wrapper = mountLogin()
    await wrapper.find('#identifier').setValue('user@example.com')
    await wrapper.find('#password').setValue('secret123')
    await wrapper.find('[data-testid="login-form"]').trigger('submit')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  it('shows error on invalid credentials (non-429)', async () => {
    loginSpy.mockRejectedValue({ response: { status: 401 } })
    const wrapper = mountLogin()
    await wrapper.find('#identifier').setValue('bad@example.com')
    await wrapper.find('#password').setValue('wrong')
    await wrapper.find('[data-testid="login-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Invalid email or password')
  })

  it('shows rate limit error on 429', async () => {
    loginSpy.mockRejectedValue({ response: { status: 429 } })
    const wrapper = mountLogin()
    await wrapper.find('#identifier').setValue('user@example.com')
    await wrapper.find('#password').setValue('pass')
    await wrapper.find('[data-testid="login-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Too many attempts')
  })

  it('disables submit button while loading', async () => {
    let resolve: () => void
    loginSpy.mockImplementation(() => new Promise<void>((r) => { resolve = r }))
    const wrapper = mountLogin()
    await wrapper.find('#identifier').setValue('user@example.com')
    await wrapper.find('#password').setValue('pass')
    const btn = wrapper.find('button[type="submit"]')
    await wrapper.find('[data-testid="login-form"]').trigger('submit')
    expect(btn.attributes('disabled')).toBeDefined()
    resolve!()
    await flushPromises()
    expect(btn.attributes('disabled')).toBeUndefined()
  })
})
