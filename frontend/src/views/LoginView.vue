<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppNavbar from '../components/AppNavbar.vue'

const identifier = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const router = useRouter()
const authStore = useAuthStore()

// ponytail: UX-only cooldown — resets on page refresh, not a security control.
// The backend enforces 5 req/min via rate limiter; don't remove that.
const failureCount = ref(0)
const cooldownUntil = ref(0)
const cooldownSecondsLeft = ref(0)

const isOnCooldown = computed(() => cooldownSecondsLeft.value > 0)

let cooldownTimer: ReturnType<typeof setInterval> | null = null

function startCooldownTimer() {
  if (cooldownTimer !== null) {
    clearInterval(cooldownTimer)
  }
  cooldownTimer = setInterval(() => {
    const remaining = Math.ceil((cooldownUntil.value - Date.now()) / 1000)
    if (remaining <= 0) {
      cooldownSecondsLeft.value = 0
      if (cooldownTimer !== null) {
        clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    } else {
      cooldownSecondsLeft.value = remaining
    }
  }, 200)
}

onUnmounted(() => {
  if (cooldownTimer !== null) {
    clearInterval(cooldownTimer)
  }
})

async function handleSubmit() {
  if (isOnCooldown.value) return
  error.value = ''
  loading.value = true
  try {
    await authStore.login(identifier.value, password.value)
    failureCount.value = 0
    router.push('/dashboard')
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } }).response?.status
    if (status === 429) {
      error.value = 'Too many attempts. Please wait before trying again.'
      // Reset failure count since backend is now enforcing the limit
      failureCount.value = 0
      cooldownUntil.value = 0
      cooldownSecondsLeft.value = 0
    } else {
      error.value = 'Invalid email or password'
      failureCount.value += 1
      if (failureCount.value >= 3) {
        const backoffMs = Math.min(failureCount.value * 5000, 30000)
        cooldownUntil.value = Date.now() + backoffMs
        cooldownSecondsLeft.value = Math.ceil(backoffMs / 1000)
        startCooldownTimer()
      }
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <AppNavbar />
    <div class="login-container">
      <div class="login-card">
        <form @submit.prevent="handleSubmit" data-testid="login-form">
          <div class="field">
            <label for="identifier">Email or Username</label>
            <input id="identifier" v-model="identifier" type="text" required autocomplete="username" />
          </div>
          <div class="field">
            <label for="password">Password</label>
            <input id="password" v-model="password" type="password" required autocomplete="current-password" />
          </div>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <p v-if="isOnCooldown" class="cooldown" role="status">
            Too many failed attempts. Please wait {{ cooldownSecondsLeft }}s before trying again.
          </p>
          <button type="submit" :disabled="loading || isOnCooldown">
            {{ loading ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-background);
  transition: background 0.35s ease;
}

.login-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.login-card {
  background: var(--color-background-soft);
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  width: 100%;
  max-width: 400px;
  transition: background 0.35s ease;
}

.field {
  margin-bottom: 1rem;
}

.field label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 500;
  color: var(--color-text);
}

.field input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  box-sizing: border-box;
  background: var(--color-background);
  color: var(--color-text);
  transition: background 0.35s ease, border-color 0.2s;
}

.field input:focus {
  outline: none;
  border-color: var(--color-accent);
}

button[type='submit'] {
  width: 100%;
  padding: 0.75rem;
  background: var(--color-accent);
  color: var(--color-background);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: opacity 0.2s;
}

button[type='submit']:hover:not(:disabled) {
  opacity: 0.88;
}

button[type='submit']:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

button[type='submit']:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.error {
  color: var(--color-error);
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.cooldown {
  color: var(--color-error);
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}
</style>
