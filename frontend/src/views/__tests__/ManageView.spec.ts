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
    { path: '/new', name: 'new-link', component: { template: '<div />' } },
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
  props: ['url'],
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

describe('ManageView add-link button', () => {
  it('renders a link to the New Link page at the top of the page', async () => {
    const store = setupStores()
    vi.spyOn(store, 'fetchAll').mockResolvedValue(undefined)
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    const addLink = wrapper.get('.btn-add-link')
    expect(addLink.text()).toBe('Add Link')
    expect(addLink.attributes('href')).toBe('/new')
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

  it('always calls fetchAll on mount, even when the store already holds cached URLs from a previous visit', async () => {
    // Regression guard for a Manage -> Share -> Back round trip: the store persists across
    // route changes (it is not torn down), so on remount `urlsStore.urls` may already be
    // populated. The list still renders that cached data immediately (no loading gate), so
    // this fetchAll is a background revalidation (stale-while-revalidate), not a redundant
    // blocking reload. It must stay unconditional because click_count is server-authoritative
    // and can change from OTHER users' clicks with no local mutation on this client ever
    // occurring - a "skip refetch if non-empty" guard would let a stale count linger
    // indefinitely with no way for this client to know to refresh it.
    const store = setupStores()
    store.urls = [mockUrl]
    const fetchAllSpy = vi.spyOn(store, 'fetchAll').mockResolvedValue(undefined)
    const wrapper = mount(ManageView, { global: globalOptions })
    expect(wrapper.findAll('.url-card-stub')).toHaveLength(1)
    await flushPromises()
    expect(fetchAllSpy).toHaveBeenCalledTimes(1)
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

  it('shows shareError when navigation to the share page fails', async () => {
    const pushSpy = vi.spyOn(router, 'push').mockRejectedValueOnce(new Error('chunk load failed'))
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-share').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Failed to open')
    pushSpy.mockRestore()
  })

  it('clears a previous shareError on a successful share navigation', async () => {
    const pushSpy = vi.spyOn(router, 'push').mockRejectedValueOnce(new Error('chunk load failed'))
    const wrapper = mount(ManageView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.stub-share').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)

    pushSpy.mockRestore()
    await wrapper.find('.stub-share').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('[role="alert"]')).toHaveLength(0)
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
