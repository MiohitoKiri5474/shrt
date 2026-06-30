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

const CreateURLFormStub = defineComponent({
  name: 'CreateURLForm',
  template: '<div class="create-url-form-stub" />',
})

const URLCardStub = defineComponent({
  name: 'URLCard',
  props: ['url', 'baseUrl'],
  emits: ['qr', 'stats', 'delete', 'edit'],
  template: `
    <div class="url-card-stub" :data-id="url.id">
      <button class="stub-qr" @click="$emit('qr', url.short_code)">QR</button>
      <button class="stub-stats" @click="$emit('stats', url.id)">Stats</button>
      <button class="stub-delete" @click="$emit('delete', url.id)">Delete</button>
      <button class="stub-edit" @click="$emit('edit', url.id)">Edit</button>
    </div>
  `,
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

describe('DashboardView hamburger menu', () => {
  beforeEach(() => {
    const store = setupStores()
    vi.spyOn(store, 'fetchAll').mockResolvedValue(undefined)
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
    useAuthStore().user = { email: 'admin@example.com', username: 'admin', is_admin: true, created_at: '' }
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.hamburger-btn').trigger('click')
    const menu = wrapper.find('.dropdown-menu')
    expect(menu.text()).toContain('Admin')
    expect(menu.text()).toContain('Add User')
  })
})

describe('DashboardView URL list', () => {
  it('shows empty state when no URLs', async () => {
    const store = setupStores()
    vi.spyOn(store, 'fetchAll').mockResolvedValue(undefined)
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.find('.empty').exists()).toBe(true)
  })

  it('renders a URLCard for each URL', async () => {
    const store = setupStores()
    const mockUrl2 = { ...mockUrl, id: 2, short_code: 'xyz' }
    vi.spyOn(store, 'fetchAll').mockImplementation(async () => {
      store.urls = [mockUrl, mockUrl2]
    })
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.findAll('.url-card-stub')).toHaveLength(2)
  })

  it('shows loadError when fetchAll fails', async () => {
    const store = setupStores()
    vi.spyOn(store, 'fetchAll').mockRejectedValue(new Error('network'))
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Failed to load URLs')
  })
})

describe('DashboardView delete flow', () => {
  let store: ReturnType<typeof useURLsStore>

  beforeEach(() => {
    store = setupStores()
    vi.spyOn(store, 'fetchAll').mockImplementation(async () => {
      store.urls = [mockUrl]
    })
  })

  it('opens confirm dialog when URLCard emits delete', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-delete').trigger('click')
    await flushPromises()
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled()
    expect(wrapper.find('.confirm-dialog').exists()).toBe(true)
  })

  it('calls urlsStore.remove on confirm', async () => {
    vi.spyOn(store, 'remove').mockResolvedValue(undefined)
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-delete').trigger('click')
    await flushPromises()
    await wrapper.find('.btn-confirm-delete').trigger('click')
    await flushPromises()
    expect(store.remove).toHaveBeenCalledWith(1)
  })

  it('cancels delete without calling remove', async () => {
    vi.spyOn(store, 'remove').mockResolvedValue(undefined)
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-delete').trigger('click')
    await flushPromises()
    await wrapper.find('.confirm-dialog .btn-cancel').trigger('click')
    await flushPromises()
    expect(store.remove).not.toHaveBeenCalled()
  })

  it('shows deleteError when remove fails', async () => {
    vi.spyOn(store, 'remove').mockRejectedValue(new Error('server error'))
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-delete').trigger('click')
    await flushPromises()
    await wrapper.find('.btn-confirm-delete').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Failed to delete')
  })
})

describe('DashboardView stats flow', () => {
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
    const wrapper = mount(DashboardView, { global: globalOptions })
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
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-stats').trigger('click')
    await flushPromises()
    await wrapper.find('.stats-panel button').trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.stats-panel').exists()).toBe(false)
  })

  it('shows statsError when fetchStats fails', async () => {
    vi.spyOn(store, 'fetchStats').mockRejectedValue(new Error('fail'))
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-stats').trigger('click')
    await flushPromises()
    expect(wrapper.find('.stats-panel').exists()).toBe(false)
    expect(wrapper.html()).toContain('Failed to load stats')
  })
})

describe('DashboardView QR flow', () => {
  let store: ReturnType<typeof useURLsStore>

  beforeEach(() => {
    store = setupStores()
    vi.spyOn(store, 'fetchAll').mockImplementation(async () => {
      store.urls = [mockUrl]
    })
  })

  it('opens QR dialog when URLCard emits qr', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-qr').trigger('click')
    await flushPromises()
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled()
    expect(wrapper.find('.qr-dialog').exists()).toBe(true)
    expect(wrapper.find('.qr-target').text()).toContain('abc123')
  })

  it('closes QR dialog on Close button click', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-qr').trigger('click')
    await flushPromises()
    expect(wrapper.find('.qr-image').exists()).toBe(true)
    await wrapper.find('.qr-dialog .btn-cancel').trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.qr-image').exists()).toBe(false)
  })
})

describe('DashboardView edit flow', () => {
  let store: ReturnType<typeof useURLsStore>

  beforeEach(() => {
    store = setupStores()
    vi.spyOn(store, 'fetchAll').mockImplementation(async () => {
      store.urls = [mockUrl]
    })
  })

  it('opens edit dialog when URLCard emits edit', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-edit').trigger('click')
    await flushPromises()
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled()
    expect(wrapper.find('.edit-dialog').exists()).toBe(true)
  })

  it('pre-fills short code from URL', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-edit').trigger('click')
    await flushPromises()
    const inputs = wrapper.findAll('.edit-dialog input')
    const shortCodeInput = inputs.find(i => (i.element as HTMLInputElement).value === 'abc123')
    expect(shortCodeInput).toBeDefined()
  })

  it('calls urlsStore.update on save', async () => {
    vi.spyOn(store, 'update').mockResolvedValue({ ...mockUrl })
    const wrapper = mount(DashboardView, { global: globalOptions })
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
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-edit').trigger('click')
    await flushPromises()
    await wrapper.find('.edit-dialog form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('.edit-dialog [role="alert"]').text()).toContain('Failed to update')
  })

  it('cancels edit without calling update', async () => {
    vi.spyOn(store, 'update').mockResolvedValue({ ...mockUrl })
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-edit').trigger('click')
    await flushPromises()
    await wrapper.find('.edit-dialog .btn-cancel').trigger('click')
    await wrapper.vm.$nextTick()
    expect(store.update).not.toHaveBeenCalled()
  })
})

describe('DashboardView logout', () => {
  beforeEach(() => {
    const store = setupStores()
    vi.spyOn(store, 'fetchAll').mockResolvedValue(undefined)
  })

  it('calls logout and redirects to /login', async () => {
    const authStore = useAuthStore()
    vi.spyOn(authStore, 'logout').mockResolvedValue(undefined)
    await router.push('/')
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.hamburger-btn').trigger('click')
    await wrapper.find('.dropdown-item--danger').trigger('click')
    await flushPromises()
    expect(authStore.logout).toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/login')
  })
})

describe('DashboardView username editing', () => {
  beforeEach(() => {
    const store = setupStores({ email: 'user@example.com', username: 'oldname', is_admin: false, created_at: '' })
    vi.spyOn(store, 'fetchAll').mockResolvedValue(undefined)
  })

  it('shows username input when user-item clicked', async () => {
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.hamburger-btn').trigger('click')
    await wrapper.find('.user-item').trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.username-input').exists()).toBe(true)
    expect((wrapper.find('.username-input').element as HTMLInputElement).value).toBe('oldname')
  })

  it('calls authStore.updateUsername on Save', async () => {
    const authStore = useAuthStore()
    vi.spyOn(authStore, 'updateUsername').mockResolvedValue(undefined)
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.hamburger-btn').trigger('click')
    await wrapper.find('.user-item').trigger('click')
    await wrapper.vm.$nextTick()
    await wrapper.find('.username-input').setValue('newname')
    await wrapper.find('.btn-save-username').trigger('click')
    await flushPromises()
    expect(authStore.updateUsername).toHaveBeenCalledWith('newname')
    expect(wrapper.find('.username-input').exists()).toBe(false)
  })

  it('shows usernameError when updateUsername fails', async () => {
    const authStore = useAuthStore()
    vi.spyOn(authStore, 'updateUsername').mockRejectedValue(new Error('fail'))
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.hamburger-btn').trigger('click')
    await wrapper.find('.user-item').trigger('click')
    await wrapper.vm.$nextTick()
    await wrapper.find('.btn-save-username').trigger('click')
    await flushPromises()
    expect(wrapper.find('.error-sm').text()).toContain('Failed to update username')
  })
})
