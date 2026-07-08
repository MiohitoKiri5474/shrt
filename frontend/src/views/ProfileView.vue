<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import Navbar from '../components/Navbar.vue'

const authStore = useAuthStore()

function extractStatus(e: unknown): number | undefined {
  return (e as { response?: { status?: number } }).response?.status
}

// Username section
const usernameInput = ref(authStore.user?.username ?? '')
const usernameError = ref('')
const usernameSuccess = ref('')
const usernameLoading = ref(false)

async function saveUsername() {
  usernameError.value = ''
  usernameSuccess.value = ''
  usernameLoading.value = true
  try {
    await authStore.updateUsername(usernameInput.value)
    usernameSuccess.value = 'Username updated.'
  } catch (e: unknown) {
    usernameError.value = extractStatus(e) === 409 ? 'Username already taken.' : 'Failed to update username.'
  } finally {
    usernameLoading.value = false
  }
}

// Email section
const emailPassword = ref('')
const newEmail = ref('')
const emailError = ref('')
const emailSuccess = ref('')
const emailLoading = ref(false)

async function saveEmail() {
  emailError.value = ''
  emailSuccess.value = ''
  emailLoading.value = true
  try {
    await authStore.updateEmail(emailPassword.value, newEmail.value)
    emailSuccess.value = 'Email updated.'
    emailPassword.value = ''
    newEmail.value = ''
  } catch (e: unknown) {
    const status = extractStatus(e)
    if (status === 401) emailError.value = 'Incorrect password.'
    else if (status === 409) emailError.value = 'Email already registered.'
    else emailError.value = 'Failed to update email.'
  } finally {
    emailLoading.value = false
  }
}

// Password section
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordError = ref('')
const passwordSuccess = ref('')
const passwordLoading = ref(false)

async function savePassword() {
  passwordError.value = ''
  passwordSuccess.value = ''
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = 'New passwords do not match.'
    return
  }
  if (newPassword.value.length < 12) {
    passwordError.value = 'Password must be at least 12 characters.'
    return
  }
  passwordLoading.value = true
  try {
    await authStore.updatePassword(currentPassword.value, newPassword.value)
    passwordSuccess.value = 'Password updated.'
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (e: unknown) {
    passwordError.value = extractStatus(e) === 401 ? 'Incorrect current password.' : 'Failed to update password.'
  } finally {
    passwordLoading.value = false
  }
}
</script>

<template>
  <div class="profile">
    <Navbar />

    <main class="profile-content">
      <section class="profile-card">
        <h2>Username</h2>
        <form @submit.prevent="saveUsername">
          <div class="field">
            <label for="profile-username">Username</label>
            <input
              id="profile-username"
              v-model="usernameInput"
              maxlength="50"
              pattern="[a-zA-Z0-9_-]+"
              placeholder="username"
            />
          </div>
          <p v-if="usernameError" class="error" role="alert">{{ usernameError }}</p>
          <p v-if="usernameSuccess" class="success" role="status">{{ usernameSuccess }}</p>
          <div class="actions">
            <button type="submit" class="btn-primary" :disabled="usernameLoading">
              {{ usernameLoading ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </form>
      </section>

      <section class="profile-card">
        <h2>Email</h2>
        <p class="current-value">Current: {{ authStore.user?.email }}</p>
        <form @submit.prevent="saveEmail">
          <div class="field">
            <label for="profile-email-password">Current password</label>
            <input
              id="profile-email-password"
              v-model="emailPassword"
              type="password"
              autocomplete="current-password"
              required
            />
          </div>
          <div class="field">
            <label for="profile-new-email">New email</label>
            <input
              id="profile-new-email"
              v-model="newEmail"
              type="email"
              autocomplete="email"
              required
            />
          </div>
          <p v-if="emailError" class="error" role="alert">{{ emailError }}</p>
          <p v-if="emailSuccess" class="success" role="status">{{ emailSuccess }}</p>
          <div class="actions">
            <button type="submit" class="btn-primary" :disabled="emailLoading">
              {{ emailLoading ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </form>
      </section>

      <section class="profile-card">
        <h2>Password</h2>
        <form @submit.prevent="savePassword">
          <div class="field">
            <label for="profile-current-password">Current password</label>
            <input
              id="profile-current-password"
              v-model="currentPassword"
              type="password"
              autocomplete="current-password"
              required
            />
          </div>
          <div class="field">
            <label for="profile-new-password">New password</label>
            <input
              id="profile-new-password"
              v-model="newPassword"
              type="password"
              autocomplete="new-password"
              minlength="12"
              maxlength="128"
              required
            />
          </div>
          <div class="field">
            <label for="profile-confirm-password">Confirm new password</label>
            <input
              id="profile-confirm-password"
              v-model="confirmPassword"
              type="password"
              autocomplete="new-password"
              required
            />
          </div>
          <p v-if="passwordError" class="error" role="alert">{{ passwordError }}</p>
          <p v-if="passwordSuccess" class="success" role="status">{{ passwordSuccess }}</p>
          <div class="actions">
            <button type="submit" class="btn-primary" :disabled="passwordLoading">
              {{ passwordLoading ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </form>
      </section>
    </main>
  </div>
</template>

<style scoped>
.profile {
  min-height: 100vh;
  background: var(--color-background);
}

.profile-content {
  max-width: 480px;
  margin: 0 auto;
  padding: 2rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.profile-card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.25rem;
  transition: background 0.35s ease, border-color 0.35s ease;
}

.profile-card h2 {
  margin: 0 0 1rem;
  font-size: 1rem;
  color: var(--color-heading);
}

.current-value {
  margin: -0.5rem 0 1rem;
  font-size: 0.85rem;
  color: var(--color-text);
  opacity: 0.7;
}

.field {
  margin-bottom: 1rem;
}

.field label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--color-text);
}

.field input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 0.9375rem;
  background: var(--color-background);
  color: var(--color-text);
  transition: background 0.35s ease, border-color 0.2s, color 0.35s ease;
}

.field input:focus {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
  border-color: var(--color-accent);
}

.error {
  color: var(--color-error);
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.success {
  color: var(--color-success, #22c55e);
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
}

.btn-primary {
  padding: 0.5rem 1.1rem;
  background: var(--color-accent);
  color: var(--color-background);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9375rem;
  transition: opacity 0.2s;
}

.btn-primary:hover {
  opacity: 0.85;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
