<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { authApi } from '../api/auth'

const emit = defineEmits<{ close: [] }>()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const successEmail = ref('')
const emailInput = ref<HTMLInputElement | null>(null)
const modalEl = ref<HTMLDivElement | null>(null)

let triggerEl: HTMLElement | null = null

onMounted(() => {
  triggerEl = document.activeElement as HTMLElement
  emailInput.value?.focus()
  document.addEventListener('keydown', trapFocus)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', trapFocus)
  triggerEl?.focus()
})

function trapFocus(e: KeyboardEvent) {
  if (e.key !== 'Tab' || !modalEl.value) return
  const focusable = modalEl.value.querySelectorAll<HTMLElement>(
    'button, input, [tabindex]:not([tabindex="-1"])'
  )
  if (!focusable.length) return
  const first = focusable[0]!
  const last = focusable[focusable.length - 1]!
  if (e.shiftKey) {
    if (document.activeElement === first) { e.preventDefault(); last.focus() }
  } else {
    if (document.activeElement === last) { e.preventDefault(); first.focus() }
  }
}

async function handleSubmit() {
  error.value = ''
  successEmail.value = ''
  loading.value = true
  try {
    const user = await authApi.addUser(email.value, password.value)
    successEmail.value = user.email
    email.value = ''
    password.value = ''
  } catch (e: any) {
    if (e.response?.status === 409) {
      error.value = 'Email is already taken.'
    } else {
      error.value = e.response?.data?.detail || 'Failed to create user.'
    }
  } finally {
    loading.value = false
  }
}

function handleClose() {
  email.value = ''
  password.value = ''
  error.value = ''
  successEmail.value = ''
  emit('close')
}
</script>

<template>
  <div class="modal-overlay" @click.self="handleClose">
    <div ref="modalEl" class="modal" role="dialog" aria-modal="true" aria-labelledby="add-user-title">
      <header class="modal-header">
        <h2 id="add-user-title">Add User</h2>
        <button class="close-btn" aria-label="Close" @click="handleClose">&times;</button>
      </header>

      <form class="add-user-form" @submit.prevent="handleSubmit">
        <div class="field">
          <label for="new-user-email">Email</label>
          <input
            id="new-user-email"
            ref="emailInput"
            v-model="email"
            type="email"
            placeholder="user@example.com"
            required
            autocomplete="email"
          />
        </div>
        <div class="field">
          <label for="new-user-password">Password</label>
          <input
            id="new-user-password"
            v-model="password"
            type="password"
            placeholder="••••••••"
            required
            minlength="6"
            autocomplete="new-password"
          />
        </div>

        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <p v-if="successEmail" class="success" role="status">
          User <strong>{{ successEmail }}</strong> created successfully.
        </p>

        <div class="actions">
          <button type="button" class="btn-secondary" @click="handleClose">Cancel</button>
          <button type="submit" class="btn-primary" :disabled="loading">
            {{ loading ? 'Creating…' : 'Create User' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: white;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  width: 100%;
  max-width: 420px;
  padding: 1.5rem;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.125rem;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  color: #6b7280;
  padding: 0.25rem;
}

.close-btn:hover {
  color: #111827;
}

.add-user-form .field {
  margin-bottom: 1rem;
}

.add-user-form .field label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 500;
  font-size: 0.875rem;
}

.add-user-form .field input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 0.9375rem;
}

.add-user-form .field input:focus {
  outline: 2px solid #3b82f6;
  outline-offset: 1px;
  border-color: #3b82f6;
}

.error {
  color: #dc2626;
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.success {
  color: #16a34a;
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.25rem;
}

.btn-primary {
  padding: 0.5rem 1.1rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9375rem;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 0.5rem 1.1rem;
  background: transparent;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9375rem;
}

.btn-secondary:hover {
  background: #f3f4f6;
}
</style>
