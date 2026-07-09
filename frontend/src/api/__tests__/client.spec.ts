import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Router } from 'vue-router'
import { apiClient, setRouter } from '../client'

function mockAdapter(status: number) {
  return vi.fn(async (config: import('axios').InternalAxiosRequestConfig) => {
    const response = { data: {}, status, statusText: '', headers: {}, config }
    throw { response, config, isAxiosError: true, message: `Request failed with status ${status}` }
  })
}

describe('apiClient 401 interceptor', () => {
  let router: Router

  beforeEach(() => {
    router = { push: vi.fn() } as unknown as Router
    setRouter(router)
  })

  it('redirects to login on a generic 401', async () => {
    apiClient.defaults.adapter = mockAdapter(401)

    await expect(apiClient.get('/api/auth/me')).rejects.toMatchObject({
      response: { status: 401 },
    })

    expect(router.push).toHaveBeenCalledWith({ name: 'login' })
  })

  it('does not redirect on a 401 from the email-change endpoint', async () => {
    apiClient.defaults.adapter = mockAdapter(401)

    await expect(
      apiClient.patch('/api/auth/me/email', { current_password: 'wrong', new_email: 'a@b.com' }),
    ).rejects.toMatchObject({ response: { status: 401 } })

    expect(router.push).not.toHaveBeenCalled()
  })

  it('does not redirect on a 401 from the password-change endpoint', async () => {
    apiClient.defaults.adapter = mockAdapter(401)

    await expect(
      apiClient.patch('/api/auth/me/password', {
        current_password: 'wrong',
        new_password: 'irrelevant-but-long-enough',
      }),
    ).rejects.toMatchObject({ response: { status: 401 } })

    expect(router.push).not.toHaveBeenCalled()
  })

  it('does not redirect on a 401 from a link-unlock endpoint', async () => {
    apiClient.defaults.adapter = mockAdapter(401)

    await expect(
      apiClient.post('/api/urls/abc123/unlock', { password: 'wrong' }),
    ).rejects.toMatchObject({ response: { status: 401 } })

    expect(router.push).not.toHaveBeenCalled()
  })
})
