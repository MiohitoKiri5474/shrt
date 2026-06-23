import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { useNetworkStatus, type NetworkStatus } from '../useNetworkStatus'

vi.mock('../../api/health', () => ({
  healthApi: { check: vi.fn() },
}))

import { healthApi } from '../../api/health'
const mockedCheck = vi.mocked(healthApi.check)

// Mount the composable inside a host component so onMounted/onUnmounted run,
// then expose its return value for assertions.
function mountComposable() {
  let api!: NetworkStatus
  const wrapper = mount(
    defineComponent({
      setup() {
        // A large interval keeps the polling timer from firing during tests;
        // we drive checks explicitly via api.check().
        api = useNetworkStatus(1_000_000)
        return () => null
      },
    }),
  )
  return { wrapper, api: () => api }
}

describe('useNetworkStatus', () => {
  beforeEach(() => {
    mockedCheck.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reports online after an initial healthy poll', async () => {
    mockedCheck.mockResolvedValue({ status: 'ok' })
    const { wrapper, api } = mountComposable()
    await flushPromises()

    expect(api().isOnline.value).toBe(true)
    expect(api().showBanner.value).toBe(false)
    wrapper.unmount()
  })

  it('reports offline and shows the banner when the poll fails', async () => {
    mockedCheck.mockRejectedValue(new Error('network down'))
    const { wrapper, api } = mountComposable()
    await flushPromises()

    expect(api().isOnline.value).toBe(false)
    expect(api().showBanner.value).toBe(true)
    wrapper.unmount()
  })

  it('treats a non-ok status payload as offline', async () => {
    mockedCheck.mockResolvedValue({ status: 'degraded' })
    const { wrapper, api } = mountComposable()
    await flushPromises()

    expect(api().isOnline.value).toBe(false)
    wrapper.unmount()
  })

  it('dismissBanner hides the banner while staying offline', async () => {
    mockedCheck.mockRejectedValue(new Error('network down'))
    const { wrapper, api } = mountComposable()
    await flushPromises()

    api().dismissBanner()
    expect(api().showBanner.value).toBe(false)
    expect(api().isOnline.value).toBe(false)
    wrapper.unmount()
  })

  it('re-shows the banner after recovery then a new outage', async () => {
    mockedCheck.mockRejectedValue(new Error('network down'))
    const { wrapper, api } = mountComposable()
    await flushPromises()
    api().dismissBanner()
    expect(api().showBanner.value).toBe(false)

    // Recover: dismissal should reset so the next drop is visible again.
    mockedCheck.mockResolvedValue({ status: 'ok' })
    await api().check()
    expect(api().isOnline.value).toBe(true)

    mockedCheck.mockRejectedValue(new Error('network down again'))
    await api().check()
    expect(api().showBanner.value).toBe(true)
    wrapper.unmount()
  })
})
