<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { urlsApi } from '../api/urls'
import { filesApi } from '../api/files'

const route = useRoute()
const code = route.params.code as string
// GET /f/{code} redirects here as `/p/{code}?type=file` when password-protected
// and visited with no token (see backend routers/files.py::serve_file) — same
// gate component links already use, just a different unlock call + destination.
const isFile = computed(() => route.query.type === 'file')

const password = ref('')
const error = ref('')
const loading = ref(false)

function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' || parsed.protocol === 'http:'
  } catch {
    return false
  }
}

async function handleUnlock() {
  error.value = ''
  loading.value = true
  try {
    if (isFile.value) {
      const { download_url } = await filesApi.unlock(code, password.value)
      window.location.href = filesApi.resolveDownloadUrl(download_url)
      return
    }
    const { redirect_url } = await urlsApi.unlock(code, password.value)
    if (!isSafeUrl(redirect_url)) {
      error.value = 'Destination URL is invalid.'
      return
    }
    window.location.href = redirect_url
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } }).response?.status
    if (status === 401) {
      error.value = 'Incorrect password. Please try again.'
    } else if (status === 404) {
      error.value = isFile.value ? 'File not found.' : 'Link not found.'
    } else if (status === 410) {
      error.value = isFile.value ? 'This file has expired.' : 'This link has expired.'
    } else {
      error.value = 'Something went wrong. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="gate-container">
    <div class="gate-card">
      <span class="gate-icon" aria-hidden="true">🔒</span>
      <h1>Password Required</h1>
      <p class="gate-subtitle">This link is password protected. Enter the password to continue.</p>
      <form @submit.prevent="handleUnlock">
        <div class="field">
          <label for="gate-password">Password</label>
          <input
            id="gate-password"
            v-model="password"
            type="password"
            placeholder="Enter password"
            required
            autofocus
            autocomplete="current-password"
          />
        </div>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Checking…' : 'Continue' }}
        </button>
      </form>
    </div>
  </main>
</template>

<style scoped>
.gate-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 1rem;
  background: var(--color-background);
}

.gate-card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 2rem 2.5rem;
  max-width: 400px;
  width: 100%;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.gate-icon {
  font-size: 2.5rem;
  display: block;
  margin-bottom: 0.75rem;
}

h1 {
  font-size: 1.5rem;
  color: var(--color-heading);
  margin-bottom: 0.5rem;
}

.gate-subtitle {
  color: var(--color-text);
  opacity: 0.7;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.field {
  margin-bottom: 1rem;
  text-align: left;
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
  transition: border-color 0.2s;
}

.field input:focus {
  outline: none;
  border-color: var(--color-accent);
}

button {
  width: 100%;
  padding: 0.65rem;
  background: var(--color-accent);
  color: var(--color-background);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  font-size: 1rem;
  transition: opacity 0.2s;
}

button:hover:not(:disabled) {
  opacity: 0.88;
}

button:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

button:disabled {
  opacity: 0.55;
}

.error {
  color: var(--color-error);
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
  text-align: left;
}
</style>
