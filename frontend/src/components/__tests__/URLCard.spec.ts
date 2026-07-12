import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import URLCard from '../URLCard.vue'
import { urlsApi } from '../../api/urls'

const mockURL = {
  id: 7,
  short_code: 'abc12345',
  original_url: 'https://example.com',
  created_at: '',
  click_count: 3,
  has_password: false,
  expires_at: null,
}

describe('URLCard', () => {
  afterEach(() => {
    // @ts-expect-error jsdom does not define navigator.clipboard by default
    delete navigator.clipboard
    // @ts-expect-error jsdom does not implement execCommand by default
    delete document.execCommand
  })

  it('emits share with the short_code when the Share button is clicked', async () => {
    const wrapper = mount(URLCard, { props: { url: mockURL } })
    await wrapper.get('.btn-share').trigger('click')
    expect(wrapper.emitted('share')).toEqual([['abc12345']])
  })

  it('emits stats and delete with the url id', async () => {
    const wrapper = mount(URLCard, { props: { url: mockURL } })
    await wrapper.get('.btn-stats').trigger('click')
    await wrapper.get('.btn-delete').trigger('click')
    expect(wrapper.emitted('stats')).toEqual([[7]])
    expect(wrapper.emitted('delete')).toEqual([[7]])
  })

  it('emits edit with the url id when the Edit button is clicked', async () => {
    const wrapper = mount(URLCard, { props: { url: mockURL } })
    await wrapper.get('.btn-edit').trigger('click')
    expect(wrapper.emitted('edit')).toEqual([[7]])
  })

  it('renders the short URL built from urlsApi.shortUrl', () => {
    const wrapper = mount(URLCard, { props: { url: mockURL } })
    expect(wrapper.find('code').text()).toBe(urlsApi.shortUrl('abc12345'))
  })

  it('has aria-live on the copy button so status changes are announced', () => {
    const wrapper = mount(URLCard, { props: { url: mockURL } })
    expect(wrapper.find('.btn-copy').attributes('aria-live')).toBe('polite')
  })

  it('calls the clipboard API with the short URL when the copy button is clicked', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const wrapper = mount(URLCard, { props: { url: mockURL } })
    await wrapper.find('.btn-copy').trigger('click')
    expect(writeText).toHaveBeenCalledWith(urlsApi.shortUrl('abc12345'))
  })

  it('shows Copied! when the clipboard copy succeeds', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const wrapper = mount(URLCard, { props: { url: mockURL } })
    await wrapper.find('.btn-copy').trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.btn-copy').text()).toBe('Copied!')
  })

  it('shows Failed! when the execCommand clipboard fallback returns false without throwing', async () => {
    const execCommand = vi.fn().mockReturnValue(false)
    document.execCommand = execCommand
    const wrapper = mount(URLCard, { props: { url: mockURL } })
    await wrapper.find('.btn-copy').trigger('click')
    await wrapper.vm.$nextTick()
    expect(execCommand).toHaveBeenCalledWith('copy')
    expect(wrapper.find('.btn-copy').text()).toBe('Failed!')
    expect(wrapper.find('.btn-copy').classes()).toContain('btn-copy--error')
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

describe('urlsApi.shortUrl', () => {
  it('falls back to the current origin when VITE_API_BASE_URL is unset', () => {
    expect(urlsApi.shortUrl('abc12345')).toBe(`${window.location.origin}/abc12345`)
  })

  it('encodes the short code', () => {
    expect(urlsApi.shortUrl('a/b?c')).toBe(`${window.location.origin}/a%2Fb%3Fc`)
  })
})
