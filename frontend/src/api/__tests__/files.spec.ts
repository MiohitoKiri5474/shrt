import { describe, it, expect, vi } from 'vitest'

vi.mock('../client', () => ({
  apiClient: {},
  BASE_URL: 'https://api.example.com',
}))

describe('filesApi.fileUrl with a split-domain BASE_URL', () => {
  it('builds the share URL against the configured API origin, not the current origin', async () => {
    const { filesApi } = await import('../files')
    expect(filesApi.fileUrl('abc12345')).toBe('https://api.example.com/f/abc12345')
  })

  it('encodes the short code', async () => {
    const { filesApi } = await import('../files')
    expect(filesApi.fileUrl('a/b?c')).toBe('https://api.example.com/f/a%2Fb%3Fc')
  })
})
