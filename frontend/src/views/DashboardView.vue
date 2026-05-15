<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useURLsStore } from '../stores/urls'
import CreateURLForm from '../components/CreateURLForm.vue'
import URLCard from '../components/URLCard.vue'
import type { StatsOut } from '../api/urls'

const authStore = useAuthStore()
const urlsStore = useURLsStore()
const selectedStats = ref<StatsOut | null>(null)
const statsError = ref('')
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

onMounted(() => urlsStore.fetchAll())

async function handleStats(id: number) {
  statsError.value = ''
  try {
    await urlsStore.fetchStats(id)
    selectedStats.value = urlsStore.currentStats
  } catch {
    statsError.value = 'Failed to load stats'
  }
}

async function handleDelete(id: number) {
  if (!confirm('Delete this URL?')) return
  await urlsStore.remove(id)
  if (selectedStats.value?.url_id === id) selectedStats.value = null
}
</script>

<template>
  <div class="dashboard">
    <header class="dash-header">
      <h1>URL Shortener</h1>
      <div class="user-info">
        <span>{{ authStore.user?.email }}</span>
        <button @click="authStore.logout()">Sign out</button>
      </div>
    </header>
    <main class="dash-content">
      <CreateURLForm />
      <section>
        <h2>Your URLs</h2>
        <p v-if="urlsStore.urls.length === 0" class="empty">No URLs yet. Create one above.</p>
        <URLCard
          v-for="url in urlsStore.urls"
          :key="url.id"
          :url="url"
          :base-url="BASE_URL"
          @stats="handleStats"
          @delete="handleDelete"
        />
      </section>
      <aside v-if="selectedStats" class="stats-panel">
        <h3>Stats for /{{ selectedStats.short_code }}</h3>
        <p><strong>Total clicks:</strong> {{ selectedStats.total_clicks }}</p>
        <table v-if="Object.keys(selectedStats.clicks_by_date).length">
          <thead><tr><th>Date</th><th>Clicks</th></tr></thead>
          <tbody>
            <tr v-for="(count, date) in selectedStats.clicks_by_date" :key="date">
              <td>{{ date }}</td><td>{{ count }}</td>
            </tr>
          </tbody>
        </table>
        <button @click="selectedStats = null">Close</button>
      </aside>
      <p v-if="statsError" class="error">{{ statsError }}</p>
    </main>
  </div>
</template>

<style scoped>
.dashboard { min-height: 100vh; background: #f9fafb; }
.dash-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 2rem; background: white; border-bottom: 1px solid #e5e7eb; }
.dash-header h1 { margin: 0; font-size: 1.25rem; }
.user-info { display: flex; align-items: center; gap: 1rem; }
.user-info button { padding: 0.4rem 0.8rem; border: 1px solid #e5e7eb; background: transparent; border-radius: 4px; cursor: pointer; }
.dash-content { max-width: 800px; margin: 0 auto; padding: 2rem 1rem; }
.empty { color: #6b7280; }
.stats-panel { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-top: 2rem; }
.stats-panel table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
.stats-panel th, .stats-panel td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #e5e7eb; }
.error { color: #dc2626; }
</style>
