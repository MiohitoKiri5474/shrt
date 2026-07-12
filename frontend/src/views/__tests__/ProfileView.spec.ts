import { describe, it, expect, vi } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import ProfileView from '../ProfileView.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
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
    updateUsername: vi.fn(),
    updateEmail: vi.fn(),
    updatePassword: vi.fn(),
  },
}))

import * as authApiModule from '../../api/auth'

function setupStore() {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  const store = useAuthStore()
  store.$patch({ user: { email: 'user@example.com', username: 'testuser', is_admin: false, created_at: '' } })
  return store
}

const AppNavbarStub = defineComponent({
  name: 'AppNavbar',
  template: '<div class="navbar-stub" />',
})

const globalOptions = { plugins: [router], stubs: { AppNavbar: AppNavbarStub } }

describe('ProfileView username section', () => {
  it('shows success message on successful save', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updateUsername).mockResolvedValue({
      email: 'user@example.com', username: 'newname', is_admin: false, created_at: '',
    })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-username').setValue('newname')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Username updated.')
  })

  it('shows conflict error on 409', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updateUsername).mockRejectedValue({ response: { status: 409 } })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-username').setValue('taken')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Username already taken.')
  })
})

describe('ProfileView email section', () => {
  it('shows success message and clears inputs on successful save', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updateEmail).mockResolvedValue({
      email: 'new@example.com', username: 'testuser', is_admin: false, created_at: '',
    })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-email-password').setValue('currentpass123')
    await wrapper.find('#profile-new-email').setValue('new@example.com')
    const forms = wrapper.findAll('form')
    await forms[1]!.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Email updated.')
    expect((wrapper.find('#profile-new-email').element as HTMLInputElement).value).toBe('')
  })

  it('shows incorrect-password error on 401', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updateEmail).mockRejectedValue({ response: { status: 401 } })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-email-password').setValue('wrongpass123')
    await wrapper.find('#profile-new-email').setValue('new@example.com')
    const forms = wrapper.findAll('form')
    await forms[1]!.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Incorrect password.')
  })

  it('shows conflict error on 409', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updateEmail).mockRejectedValue({ response: { status: 409 } })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-email-password').setValue('currentpass123')
    await wrapper.find('#profile-new-email').setValue('taken@example.com')
    const forms = wrapper.findAll('form')
    await forms[1]!.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Email already registered.')
  })
})

describe('ProfileView password section', () => {
  it('shows client-side error when passwords do not match, without calling the API', async () => {
    setupStore()
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-current-password').setValue('currentpass123')
    await wrapper.find('#profile-new-password').setValue('newpassword456')
    await wrapper.find('#profile-confirm-password').setValue('different789012')
    const forms = wrapper.findAll('form')
    await forms[2]!.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('New passwords do not match.')
    expect(authApiModule.authApi.updatePassword).not.toHaveBeenCalled()
  })

  it('shows success message and clears inputs on successful save', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updatePassword).mockResolvedValue({ token_type: 'bearer' })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-current-password').setValue('currentpass123')
    await wrapper.find('#profile-new-password').setValue('newpassword456')
    await wrapper.find('#profile-confirm-password').setValue('newpassword456')
    const forms = wrapper.findAll('form')
    await forms[2]!.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Password updated.')
    expect((wrapper.find('#profile-current-password').element as HTMLInputElement).value).toBe('')
  })

  it('shows incorrect-password error on 401', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updatePassword).mockRejectedValue({ response: { status: 401 } })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-current-password').setValue('wrongpass123')
    await wrapper.find('#profile-new-password').setValue('newpassword456')
    await wrapper.find('#profile-confirm-password').setValue('newpassword456')
    const forms = wrapper.findAll('form')
    await forms[2]!.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Incorrect current password.')
  })
})

describe('ProfileView navbar', () => {
  it('renders AppNavbar', async () => {
    setupStore()
    const wrapper = mount(ProfileView, { global: globalOptions })
    expect(wrapper.find('.navbar-stub').exists()).toBe(true)
  })
})
