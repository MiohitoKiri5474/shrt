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
    update: vi.fn(),
  },
}))

const mockURL = {
  id: 1, short_code: 'abc12345', original_url: 'https://ex.com', created_at: '', click_count: 0,
  has_password: false, expires_at: null,
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

  it('does not let a stale in-flight fetchAll wipe a URL added by create', async () => {
    let resolveList: (v: typeof mockURL[]) => void
    vi.mocked(urlsApiModule.urlsApi.list).mockReturnValue(
      new Promise((r) => { resolveList = r }),
    )
    vi.mocked(urlsApiModule.urlsApi.create).mockResolvedValue(mockURL)
    const store = useURLsStore()

    const fetchPromise = store.fetchAll() // call A: in flight, captures the pre-create version
    await store.create('https://ex.com') // unshifts mockURL, bumps the version
    resolveList!([]) // call A resolves with stale (pre-create) data
    await fetchPromise

    expect(store.urls).toHaveLength(1)
    expect(store.urls[0]!.short_code).toBe('abc12345')
  })

  it('lets the most recently-initiated fetchAll win when two fetchAll calls overlap', async () => {
    let resolveFirst: (v: typeof mockURL[]) => void
    let resolveSecond: (v: typeof mockURL[]) => void
    const first = new Promise<typeof mockURL[]>((r) => { resolveFirst = r })
    const second = new Promise<typeof mockURL[]>((r) => { resolveSecond = r })
    vi.mocked(urlsApiModule.urlsApi.list)
      .mockReturnValueOnce(first)
      .mockReturnValueOnce(second)
    const store = useURLsStore()

    const p1 = store.fetchAll()
    const p2 = store.fetchAll()
    resolveSecond!([mockURL]) // newer call resolves first
    await p2
    resolveFirst!([]) // older call resolves after, should be discarded
    await p1

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

  it('create passes expiresAt through to the API client', async () => {
    vi.mocked(urlsApiModule.urlsApi.list).mockResolvedValue([])
    vi.mocked(urlsApiModule.urlsApi.create).mockResolvedValue(mockURL)
    const store = useURLsStore()
    await store.fetchAll()
    await store.create('https://ex.com', undefined, undefined, '2099-01-01T00:00:00.000Z')
    expect(urlsApiModule.urlsApi.create).toHaveBeenCalledWith(
      'https://ex.com', undefined, undefined, '2099-01-01T00:00:00.000Z',
    )
  })

  it('remove filters url from list', async () => {
    vi.mocked(urlsApiModule.urlsApi.list).mockResolvedValue([mockURL])
    vi.mocked(urlsApiModule.urlsApi.remove).mockResolvedValue(undefined)
    const store = useURLsStore()
    await store.fetchAll()
    await store.remove(1)
    expect(store.urls).toHaveLength(0)
  })

  it('remove keeps urls and rejects when API delete fails', async () => {
    vi.mocked(urlsApiModule.urlsApi.list).mockResolvedValue([mockURL])
    vi.mocked(urlsApiModule.urlsApi.remove).mockRejectedValue(new Error('delete failed'))
    const store = useURLsStore()
    await store.fetchAll()

    await expect(store.remove(1)).rejects.toThrow('delete failed')
    expect(store.urls).toHaveLength(1)
  })

  it('update replaces url in list', async () => {
    vi.mocked(urlsApiModule.urlsApi.list).mockResolvedValue([mockURL])
    const updated = { ...mockURL, short_code: 'newcode1' }
    vi.mocked(urlsApiModule.urlsApi.update).mockResolvedValue(updated)
    const store = useURLsStore()
    await store.fetchAll()
    await store.update(1, { short_code: 'newcode1' })
    expect(store.urls[0]!.short_code).toBe('newcode1')
  })

  it('fetchStats sets currentStats', async () => {
    const mockStats = {
      url_id: 1, short_code: 'abc12345', original_url: 'https://ex.com',
      total_clicks: 5, clicks_by_date: { '2024-01-01': 3, '2024-01-02': 2 },
    }
    vi.mocked(urlsApiModule.urlsApi.stats).mockResolvedValue(mockStats)
    const store = useURLsStore()
    await store.fetchStats(1)
    expect(store.currentStats).toEqual(mockStats)
  })
})
