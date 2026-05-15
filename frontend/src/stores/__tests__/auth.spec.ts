import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../auth'
import * as authApiModule from '../../api/auth'

vi.mock('../../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
    register: vi.fn(),
  },
}))

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('login stores token and sets user', async () => {
    vi.mocked(authApiModule.authApi.login).mockResolvedValue({ access_token: 'tok123', token_type: 'bearer' })
    vi.mocked(authApiModule.authApi.me).mockResolvedValue({ id: 1, email: 'a@b.com', created_at: '' })
    const store = useAuthStore()
    await store.login('a@b.com', 'pass')
    expect(localStorage.getItem('access_token')).toBe('tok123')
    expect(store.user?.email).toBe('a@b.com')
    expect(store.isAuthenticated).toBe(true)
  })

  it('logout clears token and user', () => {
    const store = useAuthStore()
    store.$patch({ user: { id: 1, email: 'a@b.com', created_at: '' } })
    localStorage.setItem('access_token', 'tok')
    store.logout()
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('login throws on API error', async () => {
    vi.mocked(authApiModule.authApi.login).mockRejectedValue(new Error('401'))
    const store = useAuthStore()
    await expect(store.login('bad@b.com', 'wrong')).rejects.toThrow()
  })
})
