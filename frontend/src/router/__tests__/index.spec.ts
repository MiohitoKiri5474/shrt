import { describe, it, expect } from 'vitest'
import router from '../index'

describe('router meta titles', () => {
  it.each([
    ['/login', 'Log in'],
    ['/dashboard', 'Dashboard'],
    ['/profile', 'Profile'],
    ['/admin', 'User Management'],
  ])('sets meta.title for %s', (path, expectedTitle) => {
    const match = router.resolve(path)
    expect(match.meta.title).toBe(expectedTitle)
  })
})
