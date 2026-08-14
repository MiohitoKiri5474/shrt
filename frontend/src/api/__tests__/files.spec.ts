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

describe('filesApi.resolveDownloadUrl with a split-domain BASE_URL', () => {
  it('resolves a relative download_url against the configured API origin', async () => {
    const { filesApi } = await import('../files')
    expect(filesApi.resolveDownloadUrl('/f/abc12345?token=xyz')).toBe(
      'https://api.example.com/f/abc12345?token=xyz',
    )
  })
})

describe('filesApi.upload', () => {
  it('appends the password to the form data when provided', async () => {
    const post = vi.fn().mockResolvedValue({ data: { short_code: 'abc12345' } })
    vi.doMock('../client', () => ({ apiClient: { post }, BASE_URL: 'https://api.example.com' }))
    vi.resetModules()
    const { filesApi } = await import('../files')
    const file = new File(['x'], 'a.pdf', { type: 'application/pdf' })
    await filesApi.upload(file, 'file', 'secretpw')
    const formData = post.mock.calls[0]![1] as FormData
    expect(formData.get('password')).toBe('secretpw')
  })

  it('omits the password field entirely when not provided', async () => {
    const post = vi.fn().mockResolvedValue({ data: { short_code: 'abc12345' } })
    vi.doMock('../client', () => ({ apiClient: { post }, BASE_URL: 'https://api.example.com' }))
    vi.resetModules()
    const { filesApi } = await import('../files')
    const file = new File(['x'], 'a.pdf', { type: 'application/pdf' })
    await filesApi.upload(file, 'file')
    const formData = post.mock.calls[0]![1] as FormData
    expect(formData.has('password')).toBe(false)
  })
})

describe('filesApi.unlock', () => {
  it('posts the password and returns the download_url', async () => {
    const post = vi.fn().mockResolvedValue({ data: { download_url: '/f/abc12345?token=xyz' } })
    vi.doMock('../client', () => ({ apiClient: { post }, BASE_URL: 'https://api.example.com' }))
    vi.resetModules()
    const { filesApi } = await import('../files')
    const result = await filesApi.unlock('abc12345', 'secretpw')
    expect(post).toHaveBeenCalledWith('/api/files/abc12345/unlock', { password: 'secretpw' })
    expect(result.download_url).toBe('/f/abc12345?token=xyz')
  })
})
