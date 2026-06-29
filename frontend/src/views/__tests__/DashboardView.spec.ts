import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useURLsStore } from '../../stores/urls'
import DashboardView from '../DashboardView.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/', component: { template: '<div />' } }, { path: '/login', component: { template: '<div />' } }],
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

vi.mock('../../api/urls', () => ({
  urlsApi: {
    list: vi.fn().mockResolvedValue([]),
    qrUrl: vi.fn().mockReturnValue(''),
  },
}))

vi.mock('../../api/auth', () => ({
  authApi: {
    logout: vi.fn().mockResolvedValue(undefined),
    me: vi.fn(),
  },
}))

const NetworkStatusStub = defineComponent({
  name: 'NetworkStatusIndicator',
  template: '<span class="network-status-stub" />',
})

const CreateURLFormStub = defineComponent({
  name: 'CreateURLForm',
  template: '<div class="create-url-form-stub" />',
})

const URLCardStub = defineComponent({
  name: 'URLCard',
  template: '<div class="url-card-stub" />',
})

const AddUserFormStub = defineComponent({
  name: 'AddUserForm',
  emits: ['close'],
  template: '<div class="add-user-form-stub" />',
})

const globalOptions = {
  plugins: [router],
  stubs: {
    NetworkStatusIndicator: NetworkStatusStub,
    CreateURLForm: CreateURLFormStub,
    URLCard: URLCardStub,
    AddUserForm: AddUserFormStub,
  },
}

describe('DashboardView hamburger menu', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()

    const authStore = useAuthStore()
    authStore.user = { email: 'user@example.com', username: 'testuser', is_admin: false, created_at: '' }

    const urlsStore = useURLsStore()
    urlsStore.urls = []
  })

  it('is closed by default', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()

    expect(wrapper.find('.dropdown-menu').exists()).toBe(false)
    expect(wrapper.find('.hamburger-btn').attributes('aria-expanded')).toBe('false')
  })

  it('opens on hamburger button click', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()

    await wrapper.find('.hamburger-btn').trigger('click')

    expect(wrapper.find('.dropdown-menu').exists()).toBe(true)
    expect(wrapper.find('.hamburger-btn').attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('.hamburger-btn').attributes('aria-label')).toBe('Close menu')
  })

  it('closes on second hamburger button click', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()

    await wrapper.find('.hamburger-btn').trigger('click')
    await wrapper.find('.hamburger-btn').trigger('click')

    expect(wrapper.find('.dropdown-menu').exists()).toBe(false)
    expect(wrapper.find('.hamburger-btn').attributes('aria-label')).toBe('Open menu')
  })

  it('closes on Escape key press on hamburger button', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()

    await wrapper.find('.hamburger-btn').trigger('click')
    expect(wrapper.find('.dropdown-menu').exists()).toBe(true)

    await wrapper.find('.hamburger-btn').trigger('keydown', { key: 'Escape' })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.dropdown-menu').exists()).toBe(false)
  })

  it('closes on outside click via document listener', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions, attachTo: document.body })
    await flushPromises()

    await wrapper.find('.hamburger-btn').trigger('click')
    expect(wrapper.find('.dropdown-menu').exists()).toBe(true)

    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.dropdown-menu').exists()).toBe(false)
    wrapper.unmount()
  })

  it('shows Sign out in dropdown', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()

    await wrapper.find('.hamburger-btn').trigger('click')

    expect(wrapper.find('.dropdown-item--danger').text()).toBe('Sign out')
  })

  it('hides Admin link and Add User for non-admin', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()

    await wrapper.find('.hamburger-btn').trigger('click')

    const menu = wrapper.find('.dropdown-menu')
    expect(menu.text()).not.toContain('Admin')
    expect(menu.text()).not.toContain('Add User')
  })

  it('shows Admin link and Add User for admin user', async () => {
    const authStore = useAuthStore()
    authStore.user = { email: 'admin@example.com', username: 'admin', is_admin: true, created_at: '' }

    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()

    await wrapper.find('.hamburger-btn').trigger('click')

    const menu = wrapper.find('.dropdown-menu')
    expect(menu.text()).toContain('Admin')
    expect(menu.text()).toContain('Add User')
  })
})
