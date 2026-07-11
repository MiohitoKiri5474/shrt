<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useURLsStore } from '../stores/urls'
import { urlsApi } from '../api/urls'
import AppNavbar from '../components/AppNavbar.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'

const BASE_URL = window.location.origin

const route = useRoute()
const urlsStore = useURLsStore()
const loading = ref(true)
const loadError = ref('')
const copied = ref(false)
const copyError = ref(false)
const canShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function'

const shortCode = computed(() => route.params.code as string)
const url = computed(() => urlsStore.urls.find(u => u.short_code === shortCode.value) ?? null)
const shortUrl = computed(() => `${BASE_URL}/${shortCode.value}`)
const qrSrc = computed(() => urlsApi.qrUrl(shortCode.value))
const twitterHref = computed(() => `https://twitter.com/intent/tweet?url=${encodeURIComponent(shortUrl.value)}`)
const whatsappHref = computed(() => `https://wa.me/?text=${encodeURIComponent(shortUrl.value)}`)

onMounted(async () => {
  try {
    const found = urlsStore.urls.some(u => u.short_code === shortCode.value)
    if (!found) {
      try {
        await urlsStore.fetchAll()
      } catch {
        loadError.value = 'Failed to load link data. Please refresh.'
      }
    }
  } finally {
    loading.value = false
  }
})

async function copyShortUrl() {
  copyError.value = false
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(shortUrl.value)
    } else {
      const el = document.createElement('textarea')
      el.value = shortUrl.value
      el.style.cssText = 'position:fixed;opacity:0'
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch {
    copyError.value = true
    setTimeout(() => { copyError.value = false }, 1500)
  }
}

async function nativeShare() {
  try {
    await navigator.share({ title: 'Shrt', url: shortUrl.value })
  } catch {
    // user cancelled the native share sheet — no action needed
  }
}
</script>

<template>
  <div class="share">
    <AppNavbar>
      <template #status>
        <NetworkStatusIndicator />
      </template>
    </AppNavbar>
    <main class="share-content">
      <p v-if="loading" class="loading">Loading…</p>
      <template v-else>
        <template v-if="url">
          <h2>Your short link is ready</h2>
          <div class="short-url-row">
            <code>{{ shortUrl }}</code>
            <button class="btn-copy" :class="{ 'btn-copy--error': copyError }" @click="copyShortUrl">{{ copied ? 'Copied!' : copyError ? 'Failed!' : 'Copy' }}</button>
          </div>
          <img :src="qrSrc" class="qr-image" :alt="`QR code for ${shortUrl}`" width="256" height="256" />
          <div class="share-actions">
            <button v-if="canShare" class="btn-share-native" @click="nativeShare">Share…</button>
            <a class="btn-social btn-twitter" :href="twitterHref" target="_blank" rel="noopener noreferrer">Share on X</a>
            <a class="btn-social btn-whatsapp" :href="whatsappHref" target="_blank" rel="noopener noreferrer">Share on WhatsApp</a>
          </div>
        </template>
        <p v-else :class="loadError ? 'error' : 'not-found'" :role="loadError ? 'alert' : undefined">{{ loadError || 'Link not found.' }}</p>
        <RouterLink class="back-link" :to="{ name: 'manage' }">Back to Manage</RouterLink>
      </template>
    </main>
  </div>
</template>

<style scoped>
.share {
  min-height: 100vh;
  background: var(--color-background);
}

.share-content {
  max-width: 480px;
  margin: 0 auto;
  padding: 2rem 1rem;
  text-align: center;
}

.short-url-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin: 1rem 0;
}

.short-url-row code {
  font-size: 0.95rem;
  color: var(--color-code);
  word-break: break-all;
}

.btn-copy {
  font-size: 0.8rem;
  padding: 0.3rem 0.7rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  cursor: pointer;
  background: transparent;
  color: var(--color-text);
  transition: background 0.2s;
}

.btn-copy:hover {
  background: var(--color-border);
}

.btn-copy--error {
  border-color: var(--color-error);
  color: var(--color-error);
}

.qr-image {
  display: block;
  width: 256px;
  height: 256px;
  max-width: 100%;
  margin: 0 auto 1.5rem;
  background: #fff;
  padding: 0.5rem;
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.share-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.btn-share-native,
.btn-social {
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-accent);
  background: var(--color-accent);
  color: var(--color-background);
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
  font-size: 0.9rem;
  transition: opacity 0.2s;
}

.btn-share-native:hover,
.btn-social:hover {
  opacity: 0.85;
}

.btn-share-native:focus-visible,
.btn-social:focus-visible,
.btn-copy:focus-visible,
.back-link:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.back-link {
  display: inline-block;
  margin-top: 0.5rem;
  color: var(--color-link);
}

.loading,
.not-found {
  color: var(--color-text);
  margin-bottom: 1rem;
}

.error {
  color: var(--color-error);
  margin-top: 1rem;
}
</style>
