import { defineStore } from 'pinia'
import { ref } from 'vue'
import { urlsApi, type URLOut, type StatsOut } from '../api/urls'

export const useURLsStore = defineStore('urls', () => {
  const urls = ref<URLOut[]>([])
  const currentStats = ref<StatsOut | null>(null)

  async function fetchAll() {
    urls.value = await urlsApi.list()
  }

  async function create(originalUrl: string, customCode?: string, password?: string) {
    const created = await urlsApi.create(originalUrl, customCode, password)
    urls.value.unshift(created)
    return created
  }

  async function remove(id: number) {
    await urlsApi.remove(id)
    urls.value = urls.value.filter((u) => u.id !== id)
  }

  async function fetchStats(id: number) {
    currentStats.value = await urlsApi.stats(id)
  }

  async function update(id: number, payload: Parameters<typeof urlsApi.update>[1]) {
    const updated = await urlsApi.update(id, payload)
    urls.value = urls.value.map(u => u.id === updated.id ? updated : u)
    return updated
  }

  return { urls, currentStats, fetchAll, create, remove, fetchStats, update }
})
