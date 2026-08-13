import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useFilesStore } from '../files'
import * as filesApiModule from '../../api/files'

vi.mock('../../api/files', () => ({
  filesApi: {
    list: vi.fn(),
    upload: vi.fn(),
    remove: vi.fn(),
  },
}))

const mockFile = {
  id: 1, short_code: 'abc12345', kind: 'file' as const, original_filename: 'a.pdf',
  mime_type: 'application/pdf', size_bytes: 100, created_at: '', expires_at: null,
  has_password: false,
}

describe('files store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchAll populates files', async () => {
    vi.mocked(filesApiModule.filesApi.list).mockResolvedValue([mockFile])
    const store = useFilesStore()
    await store.fetchAll()
    expect(store.files).toHaveLength(1)
    expect(store.files[0]!.short_code).toBe('abc12345')
  })

  it('does not let a stale in-flight fetchAll wipe a file added by upload', async () => {
    let resolveList: (v: typeof mockFile[]) => void
    vi.mocked(filesApiModule.filesApi.list).mockReturnValue(
      new Promise((r) => { resolveList = r }),
    )
    vi.mocked(filesApiModule.filesApi.upload).mockResolvedValue(mockFile)
    const store = useFilesStore()

    const fetchPromise = store.fetchAll()
    await store.upload(new File(['x'], 'a.pdf'), 'file')
    resolveList!([])
    await fetchPromise

    expect(store.files).toHaveLength(1)
    expect(store.files[0]!.short_code).toBe('abc12345')
  })

  it('upload prepends file to list', async () => {
    vi.mocked(filesApiModule.filesApi.list).mockResolvedValue([])
    vi.mocked(filesApiModule.filesApi.upload).mockResolvedValue(mockFile)
    const store = useFilesStore()
    await store.fetchAll()
    await store.upload(new File(['x'], 'a.pdf'), 'file')
    expect(store.files).toHaveLength(1)
    expect(store.files[0]).toEqual(mockFile)
  })

  it('remove filters file out of list', async () => {
    vi.mocked(filesApiModule.filesApi.list).mockResolvedValue([mockFile])
    vi.mocked(filesApiModule.filesApi.remove).mockResolvedValue(undefined)
    const store = useFilesStore()
    await store.fetchAll()
    await store.remove(mockFile.id)
    expect(store.files).toHaveLength(0)
  })
})
