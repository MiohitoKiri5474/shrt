import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import * as authApiModule from '../../api/auth'
import router from '../index'

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

describe('router meta titles', () => {
  it.each([
    ['/login', 'Log in'],
    ['/new', 'New Link'],
    ['/manage', 'Manage Links'],
    ['/profile', 'Profile'],
    ['/admin', 'User Management'],
  ])('sets meta.title for %s', (path, expectedTitle) => {
    const match = router.resolve(path)
    expect(match.meta.title).toBe(expectedTitle)
  })
})

describe('router guard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(authApiModule.authApi.me).mockRejectedValue(new Error('401'))
  })

  it('does not call restore() for the public password-gate route when unauthenticated', async () => {
    await router.push('/p/abc123')
    expect(authApiModule.authApi.me).not.toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('password-gate')
  })

  it('does not call restore() for the public expired route when unauthenticated', async () => {
    await router.push('/expired')
    expect(authApiModule.authApi.me).not.toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('expired')
  })

  it('still redirects to login for a requiresAuth route when unauthenticated', async () => {
    await router.push('/manage')
    expect(authApiModule.authApi.me).toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('still redirects admin-only routes away when authenticated non-admin', async () => {
    vi.mocked(authApiModule.authApi.me).mockResolvedValue({
      email: 'a@b.com',
      created_at: '',
      is_admin: false,
      username: null,
    })
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('manage')
  })

  it('resolves an arbitrary unmatched path to the not-found route without calling restore()', async () => {
    await router.push('/this/path/does/not-exist')
    expect(router.currentRoute.value.name).toBe('not-found')
    expect(authApiModule.authApi.me).not.toHaveBeenCalled()
  })
})
