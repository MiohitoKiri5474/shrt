<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useURLsStore } from '../stores/urls'
import { useThemeStore } from '../stores/theme'
import CreateURLForm from '../components/CreateURLForm.vue'
import URLCard from '../components/URLCard.vue'
import AddUserForm from '../components/AddUserForm.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'
import { urlsApi, type StatsOut } from '../api/urls'
const BASE_URL = window.location.origin

const router = useRouter()
const authStore = useAuthStore()
const urlsStore = useURLsStore()
const themeStore = useThemeStore()
const selectedStats = ref<StatsOut | null>(null)
const statsError = ref('')
const deleteError = ref('')
const loadError = ref('')
const showAddUser = ref(false)
const pendingDeleteId = ref<number | null>(null)
const dialogRef = ref<HTMLDialogElement | null>(null)
const qrShortCode = ref<string | null>(null)
const qrDialogRef = ref<HTMLDialogElement | null>(null)
const qrSrc = computed(() => (qrShortCode.value ? urlsApi.qrUrl(qrShortCode.value) : ''))
const editingUsername = ref(false)
const usernameInput = ref('')
const usernameError = ref('')

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
      <h1>URL Shortener</h1>
      <nav class="dash-nav">
        <NetworkStatusIndicator />
        <template v-if="editingUsername">
          <input
            v-model="usernameInput"
            class="username-input"
            placeholder="username"
            maxlength="50"
            @keyup.enter="saveUsername"
            @keyup.escape="editingUsername = false"
          />
          <button class="btn-save-username" @click="saveUsername">Save</button>
          <button class="btn-cancel-username" @click="editingUsername = false">Cancel</button>
          <span v-if="usernameError" class="error">{{ usernameError }}</span>
        </template>
        <template v-else>
          <span
            class="user-email"
            :title="authStore.user?.email"
            style="cursor: pointer"
            @click="startEditUsername"
          >{{ authStore.user?.username ?? authStore.user?.email }}</span>
        </template>
        <RouterLink v-if="authStore.user?.is_admin" class="btn-admin" to="/admin">Admin</RouterLink>
        <button v-if="authStore.user?.is_admin" class="btn-add-user" @click="showAddUser = true">Add User</button>
        <button
          class="theme-toggle"
          :aria-label="themeStore.isDark ? '昼モードに切り替え' : '夜モードに切り替え'"
          :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
          @click="themeStore.toggle()"
        >
          <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
        </button>
        <button class="btn-signout" @click="handleLogout">Sign out</button>
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

    <AddUserForm v-if="showAddUser" @close="showAddUser = false" />

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

.username-input {
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  width: 10rem;
}

.username-input:focus {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

.btn-save-username,
.btn-cancel-username {
  padding: 0.25rem 0.6rem;
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

.btn-admin,
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

.btn-admin {
  text-decoration: none;
  line-height: 1.4;
}

.btn-admin:hover,
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
.btn-admin:focus-visible,
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
</style>
