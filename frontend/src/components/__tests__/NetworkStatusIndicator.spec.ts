import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import NetworkStatusIndicator from '../NetworkStatusIndicator.vue'

vi.mock('../../api/health', () => ({
  healthApi: { check: vi.fn() },
}))

import { healthApi } from '../../api/health'
const mockedCheck = vi.mocked(healthApi.check)

describe('NetworkStatusIndicator', () => {
  beforeEach(() => {
    mockedCheck.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    // Clear any teleported banner left in the body between tests.
    document.body.replaceChildren()
  })

  it('renders an online status with no banner when the backend is healthy', async () => {
    mockedCheck.mockResolvedValue({ status: 'ok' })
    const wrapper = mount(NetworkStatusIndicator, { attachTo: document.body })
    await flushPromises()

    expect(wrapper.find('.net-status').classes()).not.toContain('is-offline')
    expect(wrapper.get('[role="status"]').attributes('title')).toBe('Backend online')
    expect(document.body.querySelector('.net-banner')).toBeNull()
    wrapper.unmount()
  })

  it('shows the offline banner when the backend is unreachable', async () => {
    mockedCheck.mockRejectedValue(new Error('down'))
    const wrapper = mount(NetworkStatusIndicator, { attachTo: document.body })
    await flushPromises()

    expect(wrapper.find('.net-status').classes()).toContain('is-offline')
    expect(wrapper.get('[role="status"]').attributes('title')).toBe('Backend unreachable')
    expect(document.body.querySelector('.net-banner')).not.toBeNull()
    wrapper.unmount()
  })

  it('hides the banner after the dismiss button is clicked', async () => {
    mockedCheck.mockRejectedValue(new Error('down'))
    const wrapper = mount(NetworkStatusIndicator, { attachTo: document.body })
    await flushPromises()

    const dismiss = document.body.querySelector('.net-banner-dismiss') as HTMLButtonElement | null
    expect(dismiss).not.toBeNull()
    dismiss?.click()
    await flushPromises()

    expect(document.body.querySelector('.net-banner')).toBeNull()
    wrapper.unmount()
  })
})
