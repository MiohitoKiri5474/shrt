<script setup lang="ts">
import { computed } from 'vue'
import { urlsApi, type URLOut } from '../api/urls'
import { useClipboardCopy } from '../composables/useClipboardCopy'
import Icon from './AppIcon.vue'

const props = defineProps<{ url: URLOut }>()
const emit = defineEmits<{ delete: [id: number]; stats: [id: number]; share: [shortCode: string]; edit: [id: number] }>()
const { copied, copyError, copy } = useClipboardCopy()

const shortUrl = computed(() => urlsApi.shortUrl(props.url.short_code))

const favicon = computed(() => {
  try {
    return new URL(props.url.original_url).hostname.replace(/^www\./, '').charAt(0).toUpperCase() || '?'
  } catch {
    return '?'
  }
})

const expiresSoon = computed(() => {
  if (!props.url.expires_at) return false
  const diffMs = new Date(props.url.expires_at).getTime() - Date.now()
  return diffMs > 0 && diffMs < 1000 * 60 * 60 * 24 * 3
})

function copyShortUrl() {
  return copy(shortUrl.value)
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
    <span class="favicon" aria-hidden="true">{{ favicon }}</span>
    <div class="url-info">
      <a v-if="isSafeUrl(url.original_url)" :href="url.original_url" target="_blank" rel="noopener noreferrer" class="original">
        {{ url.original_url }}
      </a>
      <span v-else class="original url-invalid" title="Invalid URL — unsafe protocol">
        {{ url.original_url }}
        <span class="url-invalid__badge" aria-label="Invalid URL">Invalid URL</span>
      </span>
      <div class="short">
        <code>{{ shortUrl }}</code>
        <button class="btn-copy" :class="{ 'btn-copy--error': copyError }" aria-live="polite" @click="copyShortUrl">{{ copied ? 'Copied!' : copyError ? 'Failed!' : 'Copy' }}</button>
      </div>
      <div class="url-meta">
        <span class="clicks"><Icon name="chart" :size="12" />{{ url.click_count }} click{{ url.click_count !== 1 ? 's' : '' }}</span>
        <span v-if="url.has_password" class="chip" title="Password protected"><Icon name="lock" :size="11" />Protected</span>
        <span
          v-if="url.expires_at"
          class="chip"
          :class="{ 'chip--warning': expiresSoon }"
          :title="`Expires ${new Date(url.expires_at).toLocaleString()}`"
        ><Icon name="clock" :size="11" />{{ new Date(url.expires_at).toLocaleDateString() }}</span>
      </div>
    </div>
    <div class="url-actions">
      <button class="btn-share" @click="emit('share', url.short_code)">Share</button>
      <button class="btn-edit" @click="emit('edit', url.id)">Edit</button>
      <button class="btn-stats" @click="emit('stats', url.id)">Stats</button>
      <button class="btn-delete" @click="emit('delete', url.id)">Delete</button>
    </div>
  </div>
</template>

<style scoped>
.url-card {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  background: var(--color-background-soft);
  padding: 0.9rem 1.1rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  margin-bottom: 0.6rem;
  transition: background 0.35s ease, border-color 0.2s ease;
}

.url-card:hover {
  border-color: var(--color-border-hover);
}

.favicon {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  background: var(--color-accent-soft);
  color: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 600;
}

.url-info {
  flex: 1;
  min-width: 0;
}

.original {
  display: block;
  font-size: 0.8rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text);
  opacity: 0.65;
}

.short {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0.1rem 0 0.3rem;
}

code {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-accent);
}

.url-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.clicks {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.78rem;
  color: var(--color-text);
  opacity: 0.6;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.72rem;
  padding: 0.12rem 0.5rem;
  border-radius: 999px;
  color: var(--color-text);
  opacity: 0.75;
  background: var(--color-background-mute);
}

.chip--warning {
  color: var(--color-warning);
  background: var(--color-warning-soft);
  opacity: 1;
}

.btn-edit {
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  color: var(--color-text);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.82rem;
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
  gap: 0.4rem;
  flex-shrink: 0;
}

.btn-share,
.btn-stats {
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-accent);
  background: transparent;
  color: var(--color-accent);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.82rem;
  transition: background 0.2s;
}

.btn-share:hover,
.btn-stats:hover {
  background: var(--color-accent-soft);
}

.btn-delete {
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-error);
  background: transparent;
  color: var(--color-error);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.82rem;
  transition: background 0.2s;
}

.btn-delete:hover {
  background: var(--color-border);
}

.btn-copy {
  font-size: 0.72rem;
  padding: 0.2rem 0.5rem;
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

.btn-share:focus-visible,
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

@media (max-width: 640px) {
  .url-card {
    flex-wrap: wrap;
  }

  .url-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
