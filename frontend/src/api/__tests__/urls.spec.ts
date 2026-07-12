import { describe, it, expect, vi } from 'vitest'

vi.mock('../client', () => ({
  apiClient: {},
  BASE_URL: 'https://api.example.com',
}))

describe('urlsApi.shortUrl with a split-domain BASE_URL', () => {
  it('builds the short URL against the configured API origin, not the current origin', async () => {
    const { urlsApi } = await import('../urls')
    expect(urlsApi.shortUrl('abc12345')).toBe('https://api.example.com/abc12345')
  })

  it('encodes the short code', async () => {
    const { urlsApi } = await import('../urls')
    expect(urlsApi.shortUrl('a/b?c')).toBe('https://api.example.com/a%2Fb%3Fc')
  })
})
