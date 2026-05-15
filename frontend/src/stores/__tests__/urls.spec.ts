import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useURLsStore } from '../urls'
import * as urlsApiModule from '../../api/urls'

vi.mock('../../api/urls', () => ({
  urlsApi: {
    list: vi.fn(),
    create: vi.fn(),
    remove: vi.fn(),
    stats: vi.fn(),
  },
}))

const mockURL = {
  id: 1, short_code: 'abc12345', original_url: 'https://ex.com', created_at: '', click_count: 0,
}

describe('urls store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchAll populates urls', async () => {
    vi.mocked(urlsApiModule.urlsApi.list).mockResolvedValue([mockURL])
    const store = useURLsStore()
    await store.fetchAll()
    expect(store.urls).toHaveLength(1)
    expect(store.urls[0]!.short_code).toBe('abc12345')
  })

  it('create prepends url to list', async () => {
    vi.mocked(urlsApiModule.urlsApi.list).mockResolvedValue([])
    vi.mocked(urlsApiModule.urlsApi.create).mockResolvedValue(mockURL)
    const store = useURLsStore()
    await store.fetchAll()
    await store.create('https://ex.com')
    expect(store.urls).toHaveLength(1)
  })

  it('remove filters url from list', async () => {
    vi.mocked(urlsApiModule.urlsApi.list).mockResolvedValue([mockURL])
    vi.mocked(urlsApiModule.urlsApi.remove).mockResolvedValue(undefined)
    const store = useURLsStore()
    await store.fetchAll()
    await store.remove(1)
    expect(store.urls).toHaveLength(0)
  })
})
