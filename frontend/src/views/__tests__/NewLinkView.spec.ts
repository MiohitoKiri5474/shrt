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
