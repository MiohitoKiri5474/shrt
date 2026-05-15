<script setup lang="ts">
import type { URLOut } from '../api/urls'

const props = defineProps<{ url: URLOut; baseUrl: string }>()
const emit = defineEmits<{ delete: [id: number]; stats: [id: number] }>()

function copyShortUrl() {
  navigator.clipboard.writeText(`${props.baseUrl}/${props.url.short_code}`)
}
</script>

<template>
  <div class="url-card" :data-testid="`url-card-${url.id}`">
    <div class="url-info">
      <a :href="url.original_url" target="_blank" rel="noopener noreferrer" class="original">
        {{ url.original_url }}
      </a>
      <div class="short">
        <code>{{ baseUrl }}/{{ url.short_code }}</code>
        <button class="btn-copy" @click="copyShortUrl">Copy</button>
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
.url-card { display: flex; justify-content: space-between; align-items: center; background: white; padding: 1rem 1.25rem; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 0.75rem; }
.url-info { flex: 1; min-width: 0; }
.original { display: block; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #1d4ed8; }
.short { display: flex; align-items: center; gap: 0.5rem; margin: 0.25rem 0; }
code { font-size: 0.875rem; color: #374151; }
.clicks { font-size: 0.8rem; color: #6b7280; }
.url-actions { display: flex; gap: 0.5rem; margin-left: 1rem; }
.btn-stats { padding: 0.4rem 0.8rem; border: 1px solid #3b82f6; background: transparent; color: #3b82f6; border-radius: 4px; cursor: pointer; }
.btn-delete { padding: 0.4rem 0.8rem; border: 1px solid #dc2626; background: transparent; color: #dc2626; border-radius: 4px; cursor: pointer; }
.btn-copy { font-size: 0.75rem; padding: 0.2rem 0.5rem; border: 1px solid #9ca3af; border-radius: 3px; cursor: pointer; background: transparent; }
</style>
