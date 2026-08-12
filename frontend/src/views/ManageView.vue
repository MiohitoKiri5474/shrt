<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useURLsStore } from '../stores/urls'
import { useFilesStore } from '../stores/files'
import URLCard from '../components/URLCard.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'
import AppNavbar from '../components/AppNavbar.vue'
import Icon from '../components/Icon.vue'
import type { StatsOut, URLOut } from '../api/urls'
import { filesApi, type FileOut } from '../api/files'
import { goToShare } from '../router/navigation'

const router = useRouter()
const urlsStore = useURLsStore()
const filesStore = useFilesStore()
const filesLoadError = ref('')
const filesDeleteError = ref('')
const search = ref('')
const filteredUrls = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return urlsStore.urls
  return urlsStore.urls.filter(u =>
    u.short_code.toLowerCase().includes(q) || u.original_url.toLowerCase().includes(q),
  )
})
const selectedStats = ref<StatsOut | null>(null)
const statsError = ref('')
const deleteError = ref('')
const loadError = ref('')
const shareError = ref('')
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
  // Always revalidate on mount, even though the store may already hold cached URLs from a
  // previous visit (e.g. a Manage -> Share -> Back round trip; the store persists across
  // route changes). The list below renders that cached data immediately with no loading
  // gate, so this is a stale-while-revalidate refresh, not a blocking reload, and its only
  // cost is one background GET. It must stay unconditional: click_count is
  // server-authoritative and can change from OTHER users' clicks with no local mutation ever
  // happening on this client, so a "skip refetch if the store is non-empty" guard would let
  // a stale count linger indefinitely. Unlike ShareView (one record, safe to trust a local
  // cache hit), Manage owns the freshness of an entire list.
  urlsStore.fetchAll().catch(() => {
    loadError.value = 'Failed to load URLs. Please refresh.'
  })
  filesLoadError.value = ''
  filesStore.fetchAll().catch(() => {
    filesLoadError.value = 'Failed to load files. Please refresh.'
  })
})

// ponytail: no confirmation dialog before delete (unlike the URL delete flow's
// modal) — add one if file deletion turns out to be accident-prone in practice.
async function handleFileDelete(id: number) {
  filesDeleteError.value = ''
  try {
    await filesStore.remove(id)
  } catch {
    filesDeleteError.value = 'Failed to delete file. Please try again.'
  }
}

// Per-file inline unlock state, keyed by file id — several password-protected
// files can be listed at once, each with its own password field and error.
const fileUnlockPasswords = reactive<Record<number, string>>({})
const fileUnlockErrors = reactive<Record<number, string>>({})
const fileUnlockLoading = reactive<Record<number, boolean>>({})

async function handleFileUnlock(file: FileOut) {
  fileUnlockErrors[file.id] = ''
  const password = fileUnlockPasswords[file.id] ?? ''
  fileUnlockLoading[file.id] = true
  try {
    const { download_url } = await filesApi.unlock(file.short_code, password)
    // download_url is a relative backend path (e.g. "/f/abc123?token=..."),
    // so it must be resolved against the API origin before opening — a bare
    // relative open() would resolve against the frontend host instead.
    window.open(filesApi.resolveDownloadUrl(download_url), '_blank', 'noopener,noreferrer')
    fileUnlockPasswords[file.id] = ''
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } }).response?.status
    if (status === 401) {
      fileUnlockErrors[file.id] = 'Incorrect password.'
    } else if (status === 410) {
      fileUnlockErrors[file.id] = 'This file has expired.'
    } else if (status === 400) {
      fileUnlockErrors[file.id] = 'This file is not password protected.'
    } else {
      fileUnlockErrors[file.id] = 'Something went wrong. Please try again.'
    }
  } finally {
    fileUnlockLoading[file.id] = false
  }
}

watch(pendingDeleteId, (id) => {
  if (id !== null) {
    nextTick(() => dialogRef.value?.showModal())
  } else {
    dialogRef.value?.close()
  }
})

async function handleShare(shortCode: string) {
  shareError.value = ''
  try {
    await goToShare(router, shortCode)
  } catch (navError: unknown) {
    console.error('Failed to navigate to the share page:', navError)
    shareError.value = 'Failed to open the share page. Please try again.'
  }
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
  <div class="manage app-shell">
    <AppNavbar>
      <template #status>
        <NetworkStatusIndicator />
      </template>
    </AppNavbar>
    <main class="dash-content app-main">
      <section>
        <div class="section-header">
          <h2>Your links</h2>
          <RouterLink class="btn-add-link" to="/new"><Icon name="plus" :size="14" />Add Link</RouterLink>
        </div>
        <label class="search" v-if="urlsStore.urls.length">
          <Icon name="search" :size="14" />
          <input v-model="search" type="text" placeholder="Search links" aria-label="Search links" />
        </label>
        <p v-if="urlsStore.urls.length === 0" class="empty">No URLs yet. Create one on the New Link page.</p>
        <p v-else-if="filteredUrls.length === 0" class="empty">No links match your search.</p>
        <URLCard
          v-for="url in filteredUrls"
          :key="url.id"
          :url="url"
          @share="handleShare"
          @edit="handleEdit"
          @stats="handleStats"
          @delete="handleDelete"
        />
      </section>
      <section>
        <div class="section-header">
          <h2>Your Files</h2>
          <RouterLink class="btn-add-link" to="/new">Add File</RouterLink>
        </div>
        <p v-if="filesStore.files.length === 0" class="empty">No files or images shared yet.</p>
        <div v-for="file in filesStore.files" :key="file.id">
          <div class="file-row" data-testid="file-row">
            <div class="file-info">
              <span class="file-name">{{ file.original_filename }}</span>
              <span class="file-meta">
                {{ file.kind }} · {{ file.expires_at ? `expires ${new Date(file.expires_at).toLocaleDateString()}` : 'never expires' }}
                <span v-if="file.has_password" class="badge badge--lock" title="Password protected">🔒</span>
              </span>
            </div>
            <div v-if="file.has_password" class="file-unlock" data-testid="file-unlock">
              <input
                v-model="fileUnlockPasswords[file.id]"
                type="password"
                placeholder="Password"
                class="file-unlock-input"
                :aria-label="`Password for ${file.original_filename}`"
                @keyup.enter="handleFileUnlock(file)"
              />
              <button
                type="button"
                class="btn-unlock"
                :disabled="fileUnlockLoading[file.id]"
                @click="handleFileUnlock(file)"
              >
                {{ fileUnlockLoading[file.id] ? 'Unlocking…' : 'Unlock' }}
              </button>
            </div>
            <a v-else :href="filesApi.fileUrl(file.short_code)" target="_blank" rel="noopener noreferrer">Open</a>
            <button class="btn-confirm-delete" @click="handleFileDelete(file.id)">Delete</button>
          </div>
          <p v-if="fileUnlockErrors[file.id]" class="error file-unlock-error" role="alert">{{ fileUnlockErrors[file.id] }}</p>
        </div>
        <p v-if="filesLoadError" class="error" role="alert">{{ filesLoadError }}</p>
        <p v-if="filesDeleteError" class="error" role="alert">{{ filesDeleteError }}</p>
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
      <p v-if="shareError" class="error" role="alert">{{ shareError }}</p>
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
.manage {
  min-height: 100vh;
  background: var(--color-background);
}

.dash-content {
  max-width: 760px;
  margin: 0 auto;
  padding: 2rem 1.5rem 3rem;
  width: 100%;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.section-header h2 {
  margin: 0;
  font-size: 1.15rem;
  color: var(--color-heading);
}

.search {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  opacity: 0.75;
}

.search:focus-within {
  opacity: 1;
  border-color: var(--color-border-hover);
}

.search input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--color-text);
  font-size: 0.875rem;
}

.btn-add-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  background: var(--color-accent);
  color: var(--color-background);
  border-radius: var(--radius-md);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.875rem;
  white-space: nowrap;
  transition: opacity 0.2s;
}

.btn-add-link:hover {
  opacity: 0.88;
}

.btn-add-link:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.empty {
  color: var(--color-text);
  opacity: 0.6;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.file-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.file-name {
  color: var(--color-heading);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  font-size: 0.8rem;
  color: var(--color-text);
  opacity: 0.7;
}

.badge {
  font-size: 0.75rem;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  border: 1px solid var(--color-border);
  margin-left: 0.35rem;
}

.file-unlock {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.file-unlock-input {
  padding: 0.35rem 0.5rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  font-size: 0.875rem;
  width: 9rem;
}

.file-unlock-input:focus {
  outline: none;
  border-color: var(--color-accent);
}

.btn-unlock {
  padding: 0.35rem 0.75rem;
  border: 1px solid var(--color-accent);
  background: transparent;
  color: var(--color-accent);
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background 0.2s;
}

.btn-unlock:hover:not(:disabled) {
  background: var(--color-border);
}

.btn-unlock:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.file-unlock-error {
  margin: 0 0 0.5rem;
  font-size: 0.85rem;
}

.stats-panel {
  background: var(--color-background-soft);
  padding: 1.5rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
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
  border: 1px solid var(--color-border-hover);
  border-radius: var(--radius-lg);
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
  border: 1px solid var(--color-border-hover);
  border-radius: var(--radius-lg);
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
