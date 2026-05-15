import { defineStore } from 'pinia'
import { ref } from 'vue'
import { urlsApi, type URLOut, type StatsOut } from '../api/urls'

export const useURLsStore = defineStore('urls', () => {
  const urls = ref<URLOut[]>([])
  const currentStats = ref<StatsOut | null>(null)

  async function fetchAll() {
    urls.value = await urlsApi.list()
  }

  async function create(originalUrl: string, customCode?: string) {
    const created = await urlsApi.create(originalUrl, customCode)
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

  return { urls, currentStats, fetchAll, create, remove, fetchStats }
})
