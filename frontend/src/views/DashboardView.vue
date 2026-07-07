<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useURLsStore } from '../stores/urls'
import { useThemeStore } from '../stores/theme'
import CreateURLForm from '../components/CreateURLForm.vue'
import URLCard from '../components/URLCard.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'
import { urlsApi, type StatsOut, type URLOut } from '../api/urls'
const BASE_URL = window.location.origin

const router = useRouter()
const authStore = useAuthStore()
const urlsStore = useURLsStore()
const themeStore = useThemeStore()
const selectedStats = ref<StatsOut | null>(null)
const statsError = ref('')
const deleteError = ref('')
const loadError = ref('')
const showMenu = ref(false)
const menuRef = ref<HTMLDivElement | null>(null)
const pendingDeleteId = ref<number | null>(null)
const dialogRef = ref<HTMLDialogElement | null>(null)
const qrShortCode = ref<string | null>(null)
const qrDialogRef = ref<HTMLDialogElement | null>(null)
const qrSrc = computed(() => (qrShortCode.value ? urlsApi.qrUrl(qrShortCode.value) : ''))
const editDialogRef = ref<HTMLDialogElement | null>(null)
const editingUrl = ref<URLOut | null>(null)
const editShortCode = ref('')
const editPassword = ref('')
const editRemovePassword = ref(false)
const editExpiresAt = ref('')
const editError = ref('')
const editingUsername = ref(false)
const usernameInput = ref('')
const usernameError = ref('')

function handleOutsideClick(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    showMenu.value = false
  }
}

function startEditUsername() {
  usernameInput.value = authStore.user?.username ?? ''
  usernameError.value = ''
  editingUsername.value = true
}

async function saveUsername() {
  usernameError.value = ''
  try {
    await authStore.updateUsername(usernameInput.value)
    editingUsername.value = false
  } catch {
    usernameError.value = 'Failed to update username'
  }
}

onMounted(() => {
  loadError.value = ''
  urlsStore.fetchAll().catch(() => {
    loadError.value = 'Failed to load URLs. Please refresh.'
  })
  document.addEventListener('click', handleOutsideClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleOutsideClick)
})

watch(pendingDeleteId, (id) => {
  if (id !== null) {
    nextTick(() => dialogRef.value?.showModal())
  } else {
    dialogRef.value?.close()
  }
})

watch(qrShortCode, (code) => {
  if (code !== null) {
    nextTick(() => qrDialogRef.value?.showModal())
  } else {
    qrDialogRef.value?.close()
  }
})

function handleQr(shortCode: string) {
  qrShortCode.value = shortCode
}

function closeQr() {
  qrShortCode.value = null
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

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="dashboard">
    <header class="dash-header">
      <h1>Shrt</h1>
      <nav class="dash-nav">
        <NetworkStatusIndicator />
        <button
          class="theme-toggle"
          :aria-label="themeStore.isDark ? '昼モードに切り替え' : '夜モードに切り替え'"
          :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
          @click="themeStore.toggle()"
        >
          <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
        </button>
        <div ref="menuRef" class="hamburger-wrapper">
          <button
            class="hamburger-btn"
            :aria-expanded="showMenu"
            aria-haspopup="true"
            :aria-label="showMenu ? 'Close menu' : 'Open menu'"
            @keydown.esc.prevent="showMenu = false"
            @click.stop="showMenu = !showMenu"
          >
            <span class="bar" />
            <span class="bar" />
            <span class="bar" />
          </button>
          <div v-if="showMenu" class="dropdown-menu" role="menu" @keydown.esc.prevent="showMenu = false">
            <div class="dropdown-user">
              <template v-if="editingUsername">
                <input
                  v-model="usernameInput"
                  class="username-input"
                  placeholder="username"
                  maxlength="50"
                  @keyup.enter="saveUsername"
                  @keyup.escape="editingUsername = false"
                />
                <div class="username-actions">
                  <button class="btn-save-username" @click="saveUsername">Save</button>
                  <button class="btn-cancel-username" @click="editingUsername = false">Cancel</button>
                </div>
                <span v-if="usernameError" class="error-sm">{{ usernameError }}</span>
              </template>
              <template v-else>
                <button class="dropdown-item user-item" role="menuitem" @click="startEditUsername">
                  <span class="user-display">{{ authStore.user?.username ?? authStore.user?.email }}</span>
                  <span class="edit-hint">edit</span>
                </button>
              </template>
            </div>
            <hr class="dropdown-sep" />
            <RouterLink
              v-if="authStore.user?.is_admin"
              class="dropdown-item"
              to="/admin"
              role="menuitem"
              @click="showMenu = false"
            >Admin</RouterLink>
            <hr v-if="authStore.user?.is_admin" class="dropdown-sep" />
            <button class="dropdown-item dropdown-item--danger" role="menuitem" @click="handleLogout">Sign out</button>
          </div>
        </div>
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
          @qr="handleQr"
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
      ref="qrDialogRef"
      class="qr-dialog"
      aria-modal="true"
      aria-labelledby="qr-title"
      @close="closeQr"
    >
      <h3 id="qr-title">QR code</h3>
      <p class="qr-target">{{ BASE_URL }}/{{ qrShortCode }}</p>
      <img v-if="qrSrc" :src="qrSrc" class="qr-image" :alt="`QR code for ${BASE_URL}/${qrShortCode}`" width="256" height="256" />
      <div class="qr-actions">
        <a v-if="qrSrc" class="btn-qr-download" :href="qrSrc" :download="`qr-${qrShortCode}.png`">Download</a>
        <button class="btn-cancel" autofocus @click="closeQr">Close</button>
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

.theme-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.hamburger-wrapper {
  position: relative;
}

.hamburger-btn {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  width: 2.1rem;
  height: 2.1rem;
  padding: 0.35rem;
  background: transparent;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.hamburger-btn:hover {
  background: var(--color-border);
}

.hamburger-btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.bar {
  display: block;
  width: 100%;
  height: 2px;
  background: var(--color-text);
  border-radius: 2px;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 200px;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  padding: 0.25rem 0;
  z-index: 100;
}

.dropdown-user {
  padding: 0.5rem 0.75rem;
}

.dropdown-sep {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: 0.25rem 0;
}

.dropdown-item {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  color: var(--color-text);
  text-decoration: none;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
}

.dropdown-item:hover {
  background: var(--color-background-mute);
}

.dropdown-item:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}

.dropdown-item--danger {
  color: var(--color-error);
}

.user-item {
  justify-content: space-between;
  gap: 0.5rem;
}

.user-display {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  opacity: 0.85;
  font-weight: 500;
}

.edit-hint {
  font-size: 0.75rem;
  opacity: 0.5;
  flex-shrink: 0;
}

.username-input {
  width: 100%;
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  box-sizing: border-box;
}

.username-input:focus {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

.username-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.4rem;
}

.btn-save-username,
.btn-cancel-username {
  flex: 1;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--color-text);
  transition: background 0.2s;
}

.btn-save-username:hover,
.btn-cancel-username:hover {
  background: var(--color-border);
}

.error-sm {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.78rem;
  color: var(--color-error);
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

.qr-dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  padding: 1.5rem;
  max-width: 340px;
  width: 90%;
  text-align: center;
  z-index: 200;
}

.qr-dialog h3 {
  margin: 0 0 0.5rem;
  color: var(--color-heading);
}

.qr-target {
  margin: 0 0 1rem;
  font-size: 0.85rem;
  color: var(--color-text);
  opacity: 0.7;
  word-break: break-all;
}

.qr-image {
  display: block;
  width: 256px;
  height: 256px;
  max-width: 100%;
  margin: 0 auto 1.25rem;
  background: #fff;
  padding: 0.5rem;
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.qr-actions {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
}

.btn-qr-download {
  padding: 0.4rem 1rem;
  border: 1px solid var(--color-accent);
  background: var(--color-accent);
  color: var(--color-background);
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
  font-size: 0.9rem;
  transition: opacity 0.2s;
}

.btn-qr-download:hover {
  opacity: 0.85;
}

.btn-qr-download:focus-visible,
.qr-actions .btn-cancel:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
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
