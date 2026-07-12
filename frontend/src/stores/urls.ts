import { defineStore } from 'pinia'
import { ref } from 'vue'
import { urlsApi, type URLOut, type StatsOut } from '../api/urls'

export const useURLsStore = defineStore('urls', () => {
  const urls = ref<URLOut[]>([])
  const currentStats = ref<StatsOut | null>(null)

  // Monotonically increasing version of "local truth". Bumped whenever `urls`
  // is authoritatively updated (fetchAll starting, or create/remove/update
  // writing a local mutation), so a slow fetchAll() that resolves after a
  // newer mutation already changed the store can detect it's stale and
  // discard its (now outdated) result instead of overwriting fresher data.
  let version = 0

  async function fetchAll() {
    const requestVersion = ++version
    const result = await urlsApi.list()
    if (requestVersion === version) {
      urls.value = result
    }
  }

  async function create(originalUrl: string, customCode?: string, password?: string, expiresAt?: string) {
    const created = await urlsApi.create(originalUrl, customCode, password, expiresAt)
    version++
    urls.value.unshift(created)
    return created
  }

  async function remove(id: number) {
    await urlsApi.remove(id)
    version++
    urls.value = urls.value.filter((u) => u.id !== id)
  }

  async function fetchStats(id: number) {
    currentStats.value = await urlsApi.stats(id)
  }

  async function update(id: number, payload: Parameters<typeof urlsApi.update>[1]) {
    const updated = await urlsApi.update(id, payload)
    version++
    urls.value = urls.value.map(u => u.id === updated.id ? updated : u)
    return updated
  }

  return { urls, currentStats, fetchAll, create, remove, fetchStats, update }
})
