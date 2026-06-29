import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import PasswordGateView from '../PasswordGateView.vue'
import * as urlsApiModule from '../../api/urls'

vi.mock('../../api/urls', () => ({
  urlsApi: {
    unlock: vi.fn(),
  },
}))

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/p/:code', component: PasswordGateView }],
})

async function mountGate(code = 'abc123') {
  await router.push(`/p/${code}`)
  await router.isReady()
  return mount(PasswordGateView, { global: { plugins: [router] } })
}

describe('PasswordGateView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders password input and submit button', async () => {
    const wrapper = await mountGate()
    expect(wrapper.find('#gate-password').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').text()).toBe('Continue')
  })

  it('shows no error initially', async () => {
    const wrapper = await mountGate()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('calls urlsApi.unlock with code and password on submit', async () => {
    vi.mocked(urlsApiModule.urlsApi.unlock).mockResolvedValue({ redirect_url: 'https://example.com' })
    const wrapper = await mountGate('mycode')
    await wrapper.find('#gate-password').setValue('secret')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(urlsApiModule.urlsApi.unlock).toHaveBeenCalledWith('mycode', 'secret')
  })

  it('shows error on wrong password (401)', async () => {
    vi.mocked(urlsApiModule.urlsApi.unlock).mockRejectedValue({ response: { status: 401 } })
    const wrapper = await mountGate()
    await wrapper.find('#gate-password').setValue('wrong')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Incorrect password')
  })

  it('shows error on link not found (404)', async () => {
    vi.mocked(urlsApiModule.urlsApi.unlock).mockRejectedValue({ response: { status: 404 } })
    const wrapper = await mountGate()
    await wrapper.find('#gate-password').setValue('any')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Link not found')
  })

  it('shows generic error on other failures', async () => {
    vi.mocked(urlsApiModule.urlsApi.unlock).mockRejectedValue({ response: { status: 500 } })
    const wrapper = await mountGate()
    await wrapper.find('#gate-password').setValue('any')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Something went wrong')
  })

  it('disables submit button while loading', async () => {
    let resolve: (v: { redirect_url: string }) => void
    vi.mocked(urlsApiModule.urlsApi.unlock).mockImplementation(
      () => new Promise((r) => { resolve = r })
    )
    const wrapper = await mountGate()
    await wrapper.find('#gate-password').setValue('pass')
    const btn = wrapper.find('button[type="submit"]')
    await wrapper.find('form').trigger('submit')
    expect(btn.attributes('disabled')).toBeDefined()
    resolve!({ redirect_url: 'https://example.com' })
    await flushPromises()
    expect(btn.attributes('disabled')).toBeUndefined()
  })
})
