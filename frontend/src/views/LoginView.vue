<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login(email.value, password.value)
    router.push('/dashboard')
  } catch {
    error.value = 'Invalid email or password'
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
      <h1>URL Shortener</h1>
      <form @submit.prevent="handleSubmit" data-testid="login-form">
        <div class="field">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" required autocomplete="email" />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input id="password" v-model="password" type="password" required autocomplete="current-password" />
        </div>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button type="submit" :disabled="loading">
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

button[type='submit']:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.error {
  color: #dc2626;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}
</style>
