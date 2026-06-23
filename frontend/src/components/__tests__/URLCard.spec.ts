import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import URLCard from '../URLCard.vue'
import { urlsApi } from '../../api/urls'

const mockURL = {
  id: 7,
  short_code: 'abc12345',
  original_url: 'https://example.com',
  created_at: '',
  click_count: 3,
}

describe('URLCard', () => {
  it('emits qr with the short_code when the QR button is clicked', async () => {
    const wrapper = mount(URLCard, { props: { url: mockURL, baseUrl: 'http://localhost' } })
    await wrapper.get('.btn-qr').trigger('click')
    expect(wrapper.emitted('qr')).toEqual([['abc12345']])
  })

  it('emits stats and delete with the url id', async () => {
    const wrapper = mount(URLCard, { props: { url: mockURL, baseUrl: 'http://localhost' } })
    await wrapper.get('.btn-stats').trigger('click')
    await wrapper.get('.btn-delete').trigger('click')
    expect(wrapper.emitted('stats')).toEqual([[7]])
    expect(wrapper.emitted('delete')).toEqual([[7]])
  })
})

describe('urlsApi.qrUrl', () => {
  it('builds the same-origin QR endpoint URL', () => {
    expect(urlsApi.qrUrl('abc12345')).toBe('/api/urls/abc12345/qr')
  })

  it('encodes the short code', () => {
    expect(urlsApi.qrUrl('a/b?c')).toBe('/api/urls/a%2Fb%3Fc/qr')
  })
})
