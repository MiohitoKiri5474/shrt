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
