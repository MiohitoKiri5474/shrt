<script setup lang="ts">
import { ref } from 'vue'
import type { URLOut } from '../api/urls'

const props = defineProps<{ url: URLOut; baseUrl: string }>()
const emit = defineEmits<{ delete: [id: number]; stats: [id: number] }>()
const copied = ref(false)
const copyError = ref(false)

async function copyShortUrl() {
  copyError.value = false
  try {
    await navigator.clipboard.writeText(`${props.baseUrl}/${props.url.short_code}`)
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
      <span v-else class="original">{{ url.original_url }}</span>
      <div class="short">
        <code>{{ baseUrl }}/{{ url.short_code }}</code>
        <button class="btn-copy" :class="{ 'btn-copy--error': copyError }" @click="copyShortUrl">{{ copied ? 'Copied!' : copyError ? 'Failed!' : 'Copy' }}</button>
      </div>
      <span class="clicks">{{ url.click_count }} click{{ url.click_count !== 1 ? 's' : '' }}</span>
    </div>
    <div class="url-actions">
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

.clicks {
  font-size: 0.8rem;
  color: var(--color-text);
  opacity: 0.6;
}

.url-actions {
  display: flex;
  gap: 0.5rem;
  margin-left: 1rem;
}

.btn-stats {
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-accent);
  background: transparent;
  color: var(--color-accent);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

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

.btn-stats:focus-visible,
.btn-delete:focus-visible,
.btn-copy:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
</style>
