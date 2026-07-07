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
    updateUsername: vi.fn(),
    updateEmail: vi.fn(),
    updatePassword: vi.fn(),
    addUser: vi.fn(),
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
    vi.mocked(authApiModule.authApi.me).mockResolvedValue({ email: 'a@b.com', created_at: '', is_admin: false, username: null })
    const store = useAuthStore()
    await store.login('a@b.com', 'pass')
    expect(store.user?.email).toBe('a@b.com')
    expect(store.isAuthenticated).toBe(true)
  })

  it('logout clears user', async () => {
    const store = useAuthStore()
    store.$patch({ user: { email: 'a@b.com', created_at: '', is_admin: false, username: null } })
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
    vi.mocked(authApiModule.authApi.me).mockResolvedValue({ email: 'a@b.com', created_at: '', is_admin: false, username: null })
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

  it('updateEmail calls authApi and updates user', async () => {
    vi.mocked(authApiModule.authApi.updateEmail).mockResolvedValue({ email: 'new@b.com', created_at: '', is_admin: false, username: null })
    const store = useAuthStore()
    await store.updateEmail('currentpass123', 'new@b.com')
    expect(store.user?.email).toBe('new@b.com')
  })

  it('updatePassword calls authApi without mutating user', async () => {
    vi.mocked(authApiModule.authApi.updatePassword).mockResolvedValue({ token_type: 'bearer' })
    const store = useAuthStore()
    store.$patch({ user: { email: 'a@b.com', created_at: '', is_admin: false, username: null } })
    await store.updatePassword('oldpass123456', 'newpass123456')
    expect(authApiModule.authApi.updatePassword).toHaveBeenCalledWith('oldpass123456', 'newpass123456')
    expect(store.user?.email).toBe('a@b.com')
  })
})
