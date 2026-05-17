<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useURLsStore } from '../stores/urls'
import { useThemeStore } from '../stores/theme'
import CreateURLForm from '../components/CreateURLForm.vue'
import URLCard from '../components/URLCard.vue'
import AddUserForm from '../components/AddUserForm.vue'
import type { StatsOut } from '../api/urls'

const authStore = useAuthStore()
const urlsStore = useURLsStore()
const themeStore = useThemeStore()
const selectedStats = ref<StatsOut | null>(null)
const statsError = ref('')
const deleteError = ref('')
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const showAddUser = ref(false)

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
  deleteError.value = ''
  if (!confirm('Delete this URL?')) return
  try {
    await urlsStore.remove(id)
    if (selectedStats.value?.url_id === id) selectedStats.value = null
  } catch {
    deleteError.value = 'Failed to delete URL. Please try again.'
  }
}
</script>

<template>
  <div class="dashboard">
    <header class="dash-header">
      <h1>URL Shortener</h1>
      <nav class="dash-nav">
        <span class="user-email">{{ authStore.user?.email }}</span>
        <button class="btn-add-user" @click="showAddUser = true">Add User</button>
        <button
          class="theme-toggle"
          :aria-label="themeStore.isDark ? '昼モードに切り替え' : '夜モードに切り替え'"
          :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
          @click="themeStore.toggle()"
        >
          <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
        </button>
        <button class="btn-signout" @click="authStore.logout()">Sign out</button>
      </nav>
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
      <p v-if="deleteError" class="error" role="alert">{{ deleteError }}</p>
    </main>

    <AddUserForm v-if="showAddUser" @close="showAddUser = false" />
  </div>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: var(--color-background);
}

.dash-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 2rem;
  background: var(--color-background-soft);
  border-bottom: 1px solid var(--color-border);
  transition: background 0.35s ease, border-color 0.35s ease;
}

.dash-header h1 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--color-heading);
  letter-spacing: 0.02em;
}

.dash-nav {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-email {
  font-size: 0.875rem;
  color: var(--color-text);
  opacity: 0.75;
}

.theme-toggle {
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, border-color 0.2s, transform 0.2s;
  color: var(--color-text);
  padding: 0;
}

.theme-toggle:hover {
  background: var(--color-border);
  transform: rotate(15deg);
}

.btn-add-user {
  padding: 0.35rem 0.75rem;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--color-text);
  transition: background 0.2s, border-color 0.2s;
}

.btn-add-user:hover {
  background: var(--color-border);
}

.btn-signout {
  padding: 0.35rem 0.75rem;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--color-text);
  transition: background 0.2s, border-color 0.2s;
}

.btn-signout:hover {
  background: var(--color-border);
}

.theme-toggle:focus-visible,
.btn-add-user:focus-visible,
.btn-signout:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.dash-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.empty {
  color: var(--color-text);
  opacity: 0.6;
}

.stats-panel {
  background: var(--color-background-soft);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-top: 2rem;
  transition: background 0.35s ease;
}

.stats-panel table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}

.stats-panel th,
.stats-panel td {
  text-align: left;
  padding: 0.5rem;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
}

.error {
  color: var(--color-error);
}
</style>
