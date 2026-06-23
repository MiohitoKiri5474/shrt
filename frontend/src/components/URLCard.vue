<script setup lang="ts">
import { ref } from 'vue'
import type { URLOut } from '../api/urls'

const props = defineProps<{ url: URLOut; baseUrl: string }>()
const emit = defineEmits<{ delete: [id: number]; stats: [id: number]; qr: [shortCode: string]; edit: [id: number] }>()
const copied = ref(false)
const copyError = ref(false)

async function copyShortUrl() {
  copyError.value = false
  const text = `${props.baseUrl}/${props.url.short_code}`
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(text)
    } else {
      const el = document.createElement('textarea')
      el.value = text
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

function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' || parsed.protocol === 'http:'
  } catch {
    return false
  }
}

</script>

<template>
  <div class="url-card" :data-testid="`url-card-${url.id}`">
    <div class="url-info">
      <a v-if="isSafeUrl(url.original_url)" :href="url.original_url" target="_blank" rel="noopener noreferrer" class="original">
        {{ url.original_url }}
      </a>
      <span v-else class="original url-invalid" title="Invalid URL — unsafe protocol">
        {{ url.original_url }}
        <span class="url-invalid__badge" aria-label="Invalid URL">Invalid URL</span>
      </span>
      <div class="short">
        <code>{{ baseUrl }}/{{ url.short_code }}</code>
        <button class="btn-copy" :class="{ 'btn-copy--error': copyError }" @click="copyShortUrl">{{ copied ? 'Copied!' : copyError ? 'Failed!' : 'Copy' }}</button>
      </div>
      <div class="url-meta">
        <span class="clicks">{{ url.click_count }} click{{ url.click_count !== 1 ? 's' : '' }}</span>
        <span v-if="url.has_password" class="badge badge--lock" title="Password protected">🔒</span>
        <span v-if="url.expires_at" class="badge badge--expiry" :title="`Expires ${new Date(url.expires_at).toLocaleString()}`">⏰ {{ new Date(url.expires_at).toLocaleDateString() }}</span>
      </div>
    </div>
    <div class="url-actions">
      <button class="btn-qr" @click="emit('qr', url.short_code)">QR</button>
      <button class="btn-edit" @click="emit('edit', url.id)">Edit</button>
      <button class="btn-stats" @click="emit('stats', url.id)">Stats</button>
      <button class="btn-delete" @click="emit('delete', url.id)">Delete</button>
    </div>
  </div>
</template>

<style scoped>
.url-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--color-background-soft);
  padding: 1rem 1.25rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  margin-bottom: 0.75rem;
  transition: background 0.35s ease;
}

.url-info {
  flex: 1;
  min-width: 0;
}

.original {
  display: block;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-link);
}

.short {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0.25rem 0;
}

code {
  font-size: 0.875rem;
  color: var(--color-code);
}

.url-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.clicks {
  font-size: 0.8rem;
  color: var(--color-text);
  opacity: 0.6;
}

.badge {
  font-size: 0.75rem;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  border: 1px solid var(--color-border);
}

.btn-edit {
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  color: var(--color-text);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-edit:hover {
  background: var(--color-border);
}

.btn-edit:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.url-actions {
  display: flex;
  gap: 0.5rem;
  margin-left: 1rem;
}

.btn-qr,
.btn-stats {
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-accent);
  background: transparent;
  color: var(--color-accent);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-qr:hover,
.btn-stats:hover {
  background: var(--color-border);
}

.btn-delete {
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-error);
  background: transparent;
  color: var(--color-error);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-delete:hover {
  background: var(--color-border);
}

.btn-copy {
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 3px;
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

.btn-qr:focus-visible,
.btn-stats:focus-visible,
.btn-delete:focus-visible,
.btn-copy:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.url-invalid {
  text-decoration: line-through;
  opacity: 0.5;
  cursor: not-allowed;
}

.lock-badge {
  display: inline-block;
  margin-left: 0.5rem;
  font-size: 0.75rem;
  color: var(--color-accent);
  opacity: 0.85;
}

.url-invalid__badge {
  display: inline-block;
  margin-left: 0.4rem;
  padding: 0.1rem 0.35rem;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  text-decoration: none;
  color: var(--color-error, #c0392b);
  border: 1px solid var(--color-error, #c0392b);
  border-radius: 3px;
  vertical-align: middle;
  opacity: 1;
}
</style>
