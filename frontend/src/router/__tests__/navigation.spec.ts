import { describe, it, expect, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import { goToShare } from '../navigation'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/links/:code/share', name: 'share', component: { template: '<div />' } },
  ],
})

describe('goToShare', () => {
  it('navigates to the share route with the given short code', async () => {
    await goToShare(router, 'abc123')
    expect(router.currentRoute.value.name).toBe('share')
    expect(router.currentRoute.value.params.code).toBe('abc123')
  })

  it('returns the promise from router.push so navigation failures propagate', async () => {
    const error = new Error('chunk load failed')
    const pushSpy = vi.spyOn(router, 'push').mockRejectedValueOnce(error)
    await expect(goToShare(router, 'abc123')).rejects.toThrow('chunk load failed')
    pushSpy.mockRestore()
  })
})
