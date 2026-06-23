<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'

const identifier = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

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
  } catch {
    error.value = 'Invalid email or password'
    failureCount.value += 1
    if (failureCount.value >= 3) {
      const backoffMs = Math.min(failureCount.value * 5000, 30000)
      cooldownUntil.value = Date.now() + backoffMs
      cooldownSecondsLeft.value = Math.ceil(backoffMs / 1000)
      startCooldownTimer()
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-container">
    <button
      class="theme-toggle"
      :aria-label="themeStore.isDark ? '昼モードに切り替え' : '夜モードに切り替え'"
      :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
      @click="themeStore.toggle()"
    >
      <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
    </button>

    <div class="login-card">
      <h1>Shrt</h1>
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
</template>

<style scoped>
.login-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-background);
  transition: background 0.35s ease;
}

.theme-toggle {
  position: absolute;
  top: 1rem;
  right: 1rem;
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
  transition: background 0.2s, transform 0.2s;
  color: var(--color-text);
  padding: 0;
}

.theme-toggle:hover {
  background: var(--color-border);
  transform: rotate(15deg);
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

h1 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
  font-weight: 600;
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

button[type='submit']:focus-visible,
.theme-toggle:focus-visible {
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
