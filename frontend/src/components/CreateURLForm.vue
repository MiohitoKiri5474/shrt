<script setup lang="ts">
import { ref } from 'vue'
import { useURLsStore } from '../stores/urls'

const urlsStore = useURLsStore()
const originalUrl = ref('')
const customCode = ref('')
const error = ref('')
const loading = ref(false)

async function handleCreate() {
  error.value = ''
  try {
    const parsed = new URL(originalUrl.value)
    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
      error.value = 'Only http and https URLs are allowed.'
      return
    }
  } catch {
    error.value = 'Please enter a valid URL.'
    return
  }
  loading.value = true
  try {
    await urlsStore.create(originalUrl.value, customCode.value || undefined)
    originalUrl.value = ''
    customCode.value = ''
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to create URL'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="create-form" @submit.prevent="handleCreate" data-testid="create-url-form">
    <h2>Shorten a URL</h2>
    <div class="field">
      <label for="original-url">Original URL</label>
      <input id="original-url" v-model="originalUrl" type="url" placeholder="https://example.com" required />
    </div>
    <div class="field">
      <label for="custom-code">Custom code (optional)</label>
      <input id="custom-code" v-model="customCode" type="text" placeholder="my-link" />
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <button type="submit" :disabled="loading">{{ loading ? 'Creating…' : 'Create short URL' }}</button>
  </form>
</template>

<style scoped>
.create-form {
  background: var(--color-background-soft);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 2rem;
  transition: background 0.35s ease;
}

h2 {
  margin-bottom: 1rem;
  color: var(--color-heading);
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

button {
  padding: 0.6rem 1.2rem;
  background: var(--color-accent);
  color: var(--color-background);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
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
}
</style>
