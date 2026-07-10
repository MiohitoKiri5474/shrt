<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useURLsStore } from '../stores/urls'
import URLCard from '../components/URLCard.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'
import AppNavbar from '../components/AppNavbar.vue'
import type { StatsOut, URLOut } from '../api/urls'
const BASE_URL = window.location.origin

const router = useRouter()
const urlsStore = useURLsStore()
const selectedStats = ref<StatsOut | null>(null)
const statsError = ref('')
const deleteError = ref('')
const loadError = ref('')
const pendingDeleteId = ref<number | null>(null)
const dialogRef = ref<HTMLDialogElement | null>(null)
const editDialogRef = ref<HTMLDialogElement | null>(null)
const editingUrl = ref<URLOut | null>(null)
const editShortCode = ref('')
const editPassword = ref('')
const editRemovePassword = ref(false)
const editExpiresAt = ref('')
const editError = ref('')

onMounted(() => {
  loadError.value = ''
  urlsStore.fetchAll().catch(() => {
    loadError.value = 'Failed to load URLs. Please refresh.'
  })
})

watch(pendingDeleteId, (id) => {
  if (id !== null) {
    nextTick(() => dialogRef.value?.showModal())
  } else {
    dialogRef.value?.close()
  }
})

function handleShare(shortCode: string) {
  router.push({ name: 'share', params: { code: shortCode } })
}

watch(editingUrl, (url) => {
  if (url !== null) {
    nextTick(() => editDialogRef.value?.showModal())
  } else {
    editDialogRef.value?.close()
  }
})

function handleEdit(id: number) {
  const url = urlsStore.urls.find(u => u.id === id) ?? null
  if (!url) return
  editingUrl.value = url
  editShortCode.value = url.short_code
  editPassword.value = ''
  editRemovePassword.value = false
  editExpiresAt.value = url.expires_at ? url.expires_at.slice(0, 16) : ''
  editError.value = ''
}

function cancelEdit() {
  editingUrl.value = null
}

async function confirmEdit() {
  if (!editingUrl.value) return
  editError.value = ''
  try {
    const payload: Parameters<typeof urlsStore.update>[1] = { short_code: editShortCode.value }
    if (editRemovePassword.value) payload.remove_password = true
    else if (editPassword.value) payload.password = editPassword.value
    payload.expires_at = editExpiresAt.value ? new Date(editExpiresAt.value).toISOString() : null
    await urlsStore.update(editingUrl.value.id, payload)
    editingUrl.value = null
  } catch {
    editError.value = 'Failed to update link. Check the short code is unique.'
  }
}

async function handleStats(id: number) {
  statsError.value = ''
  try {
    await urlsStore.fetchStats(id)
    selectedStats.value = urlsStore.currentStats
  } catch {
    statsError.value = 'Failed to load stats'
  }
}

function handleDelete(id: number) {
  pendingDeleteId.value = id
}

async function confirmDelete() {
  if (pendingDeleteId.value === null) return
  const id = pendingDeleteId.value
  pendingDeleteId.value = null
  deleteError.value = ''
  try {
    await urlsStore.remove(id)
    if (selectedStats.value?.url_id === id) selectedStats.value = null
  } catch {
    deleteError.value = 'Failed to delete URL. Please try again.'
  }
}

function cancelDelete() {
  pendingDeleteId.value = null
}
</script>

<template>
  <div class="dashboard">
    <AppNavbar>
      <template #status>
        <NetworkStatusIndicator />
      </template>
    </AppNavbar>
    <main class="dash-content">
      <section>
        <h2>Your URLs</h2>
        <p v-if="urlsStore.urls.length === 0" class="empty">No URLs yet. Create one on the New Link page.</p>
        <URLCard
          v-for="url in urlsStore.urls"
          :key="url.id"
          :url="url"
          :base-url="BASE_URL"
          @share="handleShare"
          @edit="handleEdit"
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
      <p v-if="loadError" class="error" role="alert">{{ loadError }}</p>
      <p v-if="statsError" class="error">{{ statsError }}</p>
      <p v-if="deleteError" class="error" role="alert">{{ deleteError }}</p>
    </main>

    <dialog
      ref="dialogRef"
      class="confirm-dialog"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      aria-describedby="confirm-desc"
      @close="cancelDelete"
    >
      <h3 id="confirm-title">Delete URL</h3>
      <p id="confirm-desc">Are you sure you want to delete this short URL? This cannot be undone.</p>
      <div class="confirm-actions">
        <button class="btn-cancel" autofocus @click="cancelDelete">Cancel</button>
        <button class="btn-confirm-delete" @click="confirmDelete">Delete</button>
      </div>
    </dialog>

    <dialog
      ref="editDialogRef"
      class="edit-dialog"
      aria-modal="true"
      aria-labelledby="edit-title"
      @close="cancelEdit"
    >
      <h3 id="edit-title">Edit Link</h3>
      <form @submit.prevent="confirmEdit">
        <label>
          Short code
          <input v-model="editShortCode" minlength="3" maxlength="16" pattern="[a-zA-Z0-9_-]+" required autofocus />
        </label>
        <label>
          New password <span class="field-hint">(leave empty to keep current)</span>
          <input v-model="editPassword" type="password" autocomplete="new-password" :disabled="editRemovePassword" />
        </label>
        <label v-if="editingUrl?.has_password" class="checkbox-label">
          <input v-model="editRemovePassword" type="checkbox" />
          Remove password
        </label>
        <label>
          Expires at <span class="field-hint">(leave empty for no expiry)</span>
          <input v-model="editExpiresAt" type="datetime-local" />
        </label>
        <p v-if="editError" class="error" role="alert">{{ editError }}</p>
        <div class="confirm-actions">
          <button type="button" class="btn-cancel" @click="cancelEdit">Cancel</button>
          <button type="submit" class="btn-save">Save</button>
        </div>
      </form>
    </dialog>
  </div>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: var(--color-background);
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

.confirm-dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  padding: 1.5rem;
  max-width: 380px;
  width: 90%;
  z-index: 200;
}

.confirm-dialog h3 {
  margin: 0 0 0.5rem;
  color: var(--color-heading);
}

.confirm-dialog p {
  margin: 0 0 1.25rem;
  color: var(--color-text);
  font-size: 0.9rem;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-cancel {
  padding: 0.4rem 1rem;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  color: var(--color-text);
  transition: background 0.2s;
}

.btn-cancel:hover {
  background: var(--color-border);
}

.btn-confirm-delete {
  padding: 0.4rem 1rem;
  border: 1px solid var(--color-error);
  background: var(--color-error);
  color: var(--color-background);
  border-radius: 4px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-confirm-delete:hover {
  opacity: 0.85;
}

.edit-dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  padding: 1.5rem;
  max-width: 420px;
  width: 90%;
  z-index: 200;
}

.edit-dialog h3 {
  margin: 0 0 1rem;
  color: var(--color-heading);
}

.edit-dialog label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: var(--color-text);
  margin-bottom: 0.75rem;
}

.edit-dialog input[type="text"],
.edit-dialog input[type="password"],
.edit-dialog input[type="datetime-local"] {
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  font-size: 0.875rem;
}

.edit-dialog input:focus {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

.checkbox-label {
  flex-direction: row !important;
  align-items: center;
  gap: 0.5rem !important;
}

.field-hint {
  font-size: 0.75rem;
  opacity: 0.6;
  font-weight: normal;
}

.btn-save {
  padding: 0.4rem 1rem;
  border: 1px solid var(--color-accent);
  background: var(--color-accent);
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-save:hover {
  opacity: 0.85;
}
</style>
