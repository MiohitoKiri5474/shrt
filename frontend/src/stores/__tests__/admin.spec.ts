import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAdminStore } from '../admin'
import * as adminApiModule from '../../api/admin'

vi.mock('../../api/admin', () => ({
  adminApi: {
    listUsers: vi.fn(),
    deleteUser: vi.fn(),
  },
}))

const mockUser = {
  id: 1,
  email: 'a@b.com',
  username: null,
  is_admin: false,
  created_at: '2024-01-01T00:00:00Z',
  url_count: 3,
}

describe('admin store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchAll populates users', async () => {
    vi.mocked(adminApiModule.adminApi.listUsers).mockResolvedValue([mockUser])
    const store = useAdminStore()
    await store.fetchAll()
    expect(store.users).toHaveLength(1)
    expect(store.users[0]!.email).toBe('a@b.com')
    expect(store.users[0]!.url_count).toBe(3)
  })

  it('remove filters user from list', async () => {
    vi.mocked(adminApiModule.adminApi.listUsers).mockResolvedValue([mockUser])
    vi.mocked(adminApiModule.adminApi.deleteUser).mockResolvedValue(undefined)
    const store = useAdminStore()
    await store.fetchAll()
    await store.remove(1)
    expect(store.users).toHaveLength(0)
  })

  it('remove keeps users and rejects when API delete fails', async () => {
    vi.mocked(adminApiModule.adminApi.listUsers).mockResolvedValue([mockUser])
    vi.mocked(adminApiModule.adminApi.deleteUser).mockRejectedValue(new Error('delete failed'))
    const store = useAdminStore()
    await store.fetchAll()

    await expect(store.remove(1)).rejects.toThrow('delete failed')
    expect(store.users).toHaveLength(1)
  })
})
