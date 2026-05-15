// Ensure a functional localStorage is available in the jsdom test environment.
// Node 26 exposes its own partial localStorage on globalThis before jsdom can
// override it.  We replace it with a simple in-memory implementation so that
// tests that call localStorage.setItem / getItem / clear work correctly.

import { beforeEach } from 'vitest'

class MemoryStorage implements Storage {
  private store: Record<string, string> = {}

  get length() {
    return Object.keys(this.store).length
  }

  clear() {
    this.store = {}
  }

  getItem(key: string): string | null {
    return Object.prototype.hasOwnProperty.call(this.store, key)
      ? (this.store[key] as string)
      : null
  }

  key(index: number): string | null {
    const k = Object.keys(this.store)[index]
    return k !== undefined ? k : null
  }

  removeItem(key: string) {
    delete this.store[key]
  }

  setItem(key: string, value: string) {
    this.store[key] = String(value)
  }
}

const memStorage = new MemoryStorage()

Object.defineProperty(globalThis, 'localStorage', {
  value: memStorage,
  writable: true,
  configurable: true,
})

beforeEach(() => {
  memStorage.clear()
})
