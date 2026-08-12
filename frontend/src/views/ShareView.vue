<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useURLsStore } from '../stores/urls'
import { urlsApi } from '../api/urls'
import AppNavbar from '../components/AppNavbar.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'
import Icon from '../components/Icon.vue'
import { useClipboardCopy } from '../composables/useClipboardCopy'

const route = useRoute()
const urlsStore = useURLsStore()
const loading = ref(true)
const loadError = ref('')
const { copied, copyError, copy } = useClipboardCopy()
const shareError = ref(false)
const canShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function'

const shortCode = computed(() => route.params.code as string)
const url = computed(() => urlsStore.urls.find(u => u.short_code === shortCode.value) ?? null)
const shortUrl = computed(() => urlsApi.shortUrl(shortCode.value))
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

function copyShortUrl() {
  return copy(shortUrl.value)
}

function isAbortError(error: unknown): boolean {
  return typeof error === 'object' && error !== null && 'name' in error && (error as { name: unknown }).name === 'AbortError'
}

async function nativeShare() {
  shareError.value = false
  try {
    await navigator.share({ title: 'Shrt', url: shortUrl.value })
  } catch (error) {
    if (isAbortError(error)) {
      // user cancelled the native share sheet — no action needed
      return
    }
    shareError.value = true
    setTimeout(() => { shareError.value = false }, 1500)
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
          <Icon name="circleCheck" :size="26" class="ready-icon" />
          <h2>Your short link is ready</h2>
          <div class="short-url-row">
            <code>{{ shortUrl }}</code>
            <button class="btn-copy" :class="{ 'btn-copy--error': copyError }" aria-live="polite" @click="copyShortUrl">
              <Icon name="copy" :size="12" />{{ copied ? 'Copied!' : copyError ? 'Failed!' : 'Copy' }}
            </button>
          </div>
          <img :src="qrSrc" class="qr-image" :alt="`QR code for ${shortUrl}`" width="256" height="256" />
          <a class="btn-qr-download" :href="qrSrc" :download="`qr-${shortCode}.png`"><Icon name="download" :size="12" />Download QR</a>
          <div class="share-actions">
            <button v-if="canShare" class="btn-share-native" @click="nativeShare"><Icon name="share" :size="14" />Share…</button>
            <a class="btn-social btn-twitter" :href="twitterHref" target="_blank" rel="noopener noreferrer"><Icon name="x" :size="14" />Share on X</a>
            <a class="btn-social btn-whatsapp" :href="whatsappHref" target="_blank" rel="noopener noreferrer"><Icon name="message" :size="14" />Share on WhatsApp</a>
          </div>
          <p v-if="shareError" class="error" role="alert">Share failed. Please try again.</p>
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
  max-width: 380px;
  margin: 2rem auto;
  padding: 2rem 1.5rem;
  text-align: center;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.ready-icon {
  color: var(--color-success);
  margin-bottom: 0.5rem;
}

.share-content h2 {
  font-size: 1.05rem;
  color: var(--color-heading);
  margin: 0;
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
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  padding: 0.3rem 0.7rem;
  border: 1px solid var(--color-border-hover);
  border-radius: var(--radius-sm);
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
  margin: 0 auto 0.75rem;
  background: #fff;
  padding: 0.5rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.btn-qr-download {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 1.5rem;
  padding: 0.3rem 0.7rem;
  border: 1px solid var(--color-border-hover);
  border-radius: var(--radius-sm);
  color: var(--color-text);
  text-decoration: none;
  font-size: 0.8rem;
  transition: background 0.2s;
}

.btn-qr-download:hover {
  background: var(--color-border);
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
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-accent);
  background: var(--color-accent);
  color: var(--color-background);
  border-radius: var(--radius-md);
  cursor: pointer;
  text-decoration: none;
  font-size: 0.85rem;
  transition: opacity 0.2s;
}

.btn-share-native:hover,
.btn-social:hover {
  opacity: 0.85;
}

.btn-share-native:focus-visible,
.btn-social:focus-visible,
.btn-copy:focus-visible,
.btn-qr-download:focus-visible,
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
