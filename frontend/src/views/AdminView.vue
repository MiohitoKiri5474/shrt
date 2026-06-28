<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useAdminStore } from '../stores/admin'
import { useThemeStore } from '../stores/theme'
import AddUserForm from '../components/AddUserForm.vue'

const authStore = useAuthStore()
const adminStore = useAdminStore()
const themeStore = useThemeStore()

const showAddUserModal = ref(false)
const loadError = ref('')
const deleteError = ref('')
const pendingDeleteId = ref<number | null>(null)
const dialogRef = ref<HTMLDialogElement | null>(null)

onMounted(() => {
  loadError.value = ''
  adminStore.fetchAll().catch(() => {
    loadError.value = 'Failed to load users. Please refresh.'
  })
})

watch(pendingDeleteId, (id) => {
  if (id !== null) {
    nextTick(() => dialogRef.value?.showModal())
  } else {
    dialogRef.value?.close()
  }
})

function formatDate(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString()
}

function isSelf(email: string): boolean {
  return authStore.user?.email === email
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
    await adminStore.remove(id)
  } catch {
    deleteError.value = 'Failed to delete user. Please try again.'
  }
}

function cancelDelete() {
  pendingDeleteId.value = null
}

function handleUserAdded() {
  showAddUserModal.value = false
  adminStore.fetchAll().catch(() => {
    loadError.value = 'Failed to refresh users.'
  })
}
</script>

<template>
  <div class="admin">
    <header class="admin-header">
      <h1>User Management</h1>
      <nav class="admin-nav">
        <RouterLink class="btn-link" to="/dashboard">← Dashboard</RouterLink>
        <button class="btn-add-user" @click="showAddUserModal = true">Add User</button>
        <button
          class="theme-toggle"
          :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
          @click="themeStore.toggle()"
        >
          <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
        </button>
      </nav>
    </header>

    <main class="admin-content">
      <h2>All users</h2>
      <p v-if="!loadError && adminStore.users.length === 0" class="empty">No users found.</p>

      <table v-if="adminStore.users.length" class="user-table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Username</th>
            <th>Role</th>
            <th>Registered</th>
            <th class="num">URLs</th>
            <th class="actions-col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in adminStore.users" :key="user.id">
            <td>{{ user.email }}</td>
            <td>{{ user.username ?? '—' }}</td>
            <td>
              <span :class="['badge', user.is_admin ? 'badge-admin' : 'badge-user']">
                {{ user.is_admin ? 'Admin' : 'User' }}
              </span>
            </td>
            <td>{{ formatDate(user.created_at) }}</td>
            <td class="num">{{ user.url_count }}</td>
            <td class="actions-col">
              <button
                class="btn-delete"
                :disabled="isSelf(user.email)"
                :title="isSelf(user.email) ? 'You cannot delete your own account' : 'Delete user'"
                @click="handleDelete(user.id)"
              >
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <p v-if="loadError" class="error" role="alert">{{ loadError }}</p>
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
      <h3 id="confirm-title">Delete user</h3>
      <p id="confirm-desc">
        Are you sure you want to delete this user? Their URLs and click history will also be
        removed. This cannot be undone.
      </p>
      <div class="confirm-actions">
        <button class="btn-cancel" autofocus @click="cancelDelete">Cancel</button>
        <button class="btn-confirm-delete" @click="confirmDelete">Delete</button>
      </div>
    </dialog>

    <AddUserForm
      v-if="showAddUserModal"
      @user-added="handleUserAdded"
      @close="showAddUserModal = false"
    />
  </div>
</template>

<style scoped>
.admin {
  min-height: 100vh;
  background: var(--color-background);
}

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 2rem;
  background: var(--color-background-soft);
  border-bottom: 1px solid var(--color-border);
  transition: background 0.35s ease, border-color 0.35s ease;
}

.admin-header h1 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--color-heading);
  letter-spacing: 0.02em;
}

.admin-nav {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.btn-link {
  font-size: 0.875rem;
  color: var(--color-text);
  text-decoration: none;
  padding: 0.35rem 0.6rem;
  border-radius: 4px;
  transition: background 0.2s;
}

.btn-link:hover {
  background: var(--color-border);
}

.btn-add-user {
  padding: 0.35rem 0.75rem;
  background: var(--color-accent);
  color: var(--color-background);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: opacity 0.2s;
}

.btn-add-user:hover {
  opacity: 0.85;
}

.btn-add-user:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
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

.btn-link:focus-visible,
.theme-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.admin-content {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.admin-content h2 {
  color: var(--color-heading);
  font-size: 1.05rem;
  margin: 0 0 1rem;
}

.empty {
  color: var(--color-text);
  opacity: 0.6;
}

.user-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  transition: background 0.35s ease;
}

.user-table th,
.user-table td {
  text-align: left;
  padding: 0.65rem 0.85rem;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
  font-size: 0.9rem;
}

.user-table thead th {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  opacity: 0.7;
  font-weight: 600;
}

.user-table tbody tr:last-child td {
  border-bottom: none;
}

.user-table tbody tr:hover {
  background: var(--color-background-mute);
}

.num {
  text-align: right;
}

.actions-col {
  text-align: right;
  width: 1%;
  white-space: nowrap;
}

.badge {
  display: inline-block;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  border: 1px solid var(--color-border-hover);
}

.badge-admin {
  color: var(--color-accent);
  border-color: var(--color-accent);
}

.badge-user {
  color: var(--color-text);
  opacity: 0.7;
}

.btn-delete {
  padding: 0.3rem 0.7rem;
  border: 1px solid var(--color-error);
  background: transparent;
  color: var(--color-error);
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.82rem;
  transition: background 0.2s, color 0.2s, opacity 0.2s;
}

.btn-delete:hover:not(:disabled) {
  background: var(--color-error);
  color: var(--color-background);
}

.btn-delete:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.btn-delete:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  border-color: var(--color-border-hover);
  color: var(--color-text);
}

.error {
  color: var(--color-error);
  margin-top: 1rem;
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
  max-width: 400px;
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
</style>
