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
.create-form { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 2rem; }
h2 { margin-bottom: 1rem; }
.field { margin-bottom: 1rem; }
.field label { display: block; margin-bottom: 0.25rem; font-weight: 500; }
.field input { width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
button { padding: 0.6rem 1.2rem; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; }
button:disabled { opacity: 0.6; }
.error { color: #dc2626; font-size: 0.875rem; }
</style>
