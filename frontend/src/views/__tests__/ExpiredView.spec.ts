import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ExpiredView from '../ExpiredView.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/expired', component: ExpiredView }],
})

async function mountExpired(code?: string) {
  await router.push(code ? `/expired?code=${code}` : '/expired')
  await router.isReady()
  return mount(ExpiredView, { global: { plugins: [router] } })
}

describe('ExpiredView', () => {
  it('renders heading and subtitle', async () => {
    const wrapper = await mountExpired()
    expect(wrapper.find('h1').text()).toBe('Link Expired')
    expect(wrapper.find('.expired-subtitle').exists()).toBe(true)
  })

  it('shows code when provided in query', async () => {
    const wrapper = await mountExpired('abc123')
    expect(wrapper.find('.expired-code').text()).toContain('abc123')
  })

  it('hides code section when no code in query', async () => {
    const wrapper = await mountExpired()
    expect(wrapper.find('.expired-code').exists()).toBe(false)
  })

  it('has a link back to homepage', async () => {
    const wrapper = await mountExpired()
    const link = wrapper.find('.btn-home')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toBe('/')
  })
})
