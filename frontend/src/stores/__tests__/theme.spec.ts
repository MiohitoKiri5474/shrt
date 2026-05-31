import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useThemeStore } from '../theme'

function setupMatchMedia(prefersDark: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: vi.fn().mockReturnValue({ matches: prefersDark }),
  })
}

describe('theme store', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('dark')
    setActivePinia(createPinia())
  })

  it('defaults to light when system prefers light and no stored preference', () => {
    setupMatchMedia(false)
    const store = useThemeStore()
    expect(store.isDark).toBe(false)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('defaults to dark when system prefers dark and no stored preference', () => {
    setupMatchMedia(true)
    const store = useThemeStore()
    expect(store.isDark).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('uses stored dark preference over system light preference', () => {
    setupMatchMedia(false)
    localStorage.setItem('theme', 'dark')
    const store = useThemeStore()
    expect(store.isDark).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('uses stored light preference over system dark preference', () => {
    setupMatchMedia(true)
    localStorage.setItem('theme', 'light')
    const store = useThemeStore()
    expect(store.isDark).toBe(false)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('toggle() switches light to dark, persists to localStorage, adds .dark class', () => {
    setupMatchMedia(false)
    const store = useThemeStore()
    store.toggle()
    expect(store.isDark).toBe(true)
    expect(localStorage.getItem('theme')).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('toggle() switches dark to light, persists to localStorage, removes .dark class', () => {
    setupMatchMedia(true)
    const store = useThemeStore()
    store.toggle()
    expect(store.isDark).toBe(false)
    expect(localStorage.getItem('theme')).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})
