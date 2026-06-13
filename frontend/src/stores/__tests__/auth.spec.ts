import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../auth'
import * as authApiModule from '../../api/auth'

vi.mock('../../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
    register: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
  },
}))

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('login calls me() and sets user', async () => {
    vi.mocked(authApiModule.authApi.login).mockResolvedValue({ token_type: 'bearer' })
    vi.mocked(authApiModule.authApi.me).mockResolvedValue({ email: 'a@b.com', created_at: '', is_admin: false })
    const store = useAuthStore()
    await store.login('a@b.com', 'pass')
    expect(store.user?.email).toBe('a@b.com')
    expect(store.isAuthenticated).toBe(true)
  })

  it('logout clears user', async () => {
    const store = useAuthStore()
    store.$patch({ user: { email: 'a@b.com', created_at: '', is_admin: false } })
    await store.logout()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('login throws on API error', async () => {
    vi.mocked(authApiModule.authApi.login).mockRejectedValue(new Error('401'))
    const store = useAuthStore()
    await expect(store.login('bad@b.com', 'wrong')).rejects.toThrow('401')
  })

  it('restore sets user when me() succeeds', async () => {
    vi.mocked(authApiModule.authApi.me).mockResolvedValue({ email: 'a@b.com', created_at: '', is_admin: false })
    const store = useAuthStore()
    await store.restore()
    expect(store.user?.email).toBe('a@b.com')
    expect(store.isAuthenticated).toBe(true)
  })

  it('restore clears user without calling logout when me() fails', async () => {
    vi.mocked(authApiModule.authApi.me).mockRejectedValue(new Error('401'))
    const store = useAuthStore()
    await store.restore()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(authApiModule.authApi.logout).not.toHaveBeenCalled()
  })
})
