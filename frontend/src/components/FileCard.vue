<script setup lang="ts">
import { computed, ref } from 'vue'
import { filesApi, type FileOut } from '../api/files'
import Icon from './AppIcon.vue'

const props = defineProps<{ file: FileOut }>()
const emit = defineEmits<{ delete: [id: number] }>()

const password = ref('')
const error = ref('')
const loading = ref(false)

const expiresSoon = computed(() => {
  if (!props.file.expires_at) return false
  const diffMs = new Date(props.file.expires_at).getTime() - Date.now()
  return diffMs > 0 && diffMs < 1000 * 60 * 60 * 24 * 3
})

async function handleUnlock() {
  error.value = ''
  loading.value = true
  try {
    const { download_url } = await filesApi.unlock(props.file.short_code, password.value)
    // download_url is a relative backend path (e.g. "/f/abc123?token=..."),
    // so it must be resolved against the API origin before opening — a bare
    // relative open() would resolve against the frontend host instead.
    window.open(filesApi.resolveDownloadUrl(download_url), '_blank', 'noopener,noreferrer')
    password.value = ''
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } }).response?.status
    if (status === 401) {
      error.value = 'Incorrect password.'
    } else if (status === 410) {
      error.value = 'This file has expired.'
    } else if (status === 400) {
      error.value = 'This file is not password protected.'
    } else {
      error.value = 'Something went wrong. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="file-card" :data-testid="`file-card-${file.id}`">
    <div class="file-card-main">
      <span class="file-icon" aria-hidden="true">
        <Icon :name="file.kind === 'image' ? 'image' : 'file'" :size="16" />
      </span>
      <div class="file-info">
        <span class="file-name">{{ file.original_filename }}</span>
        <div class="file-meta">
          <span class="chip" :class="{ 'chip--warning': expiresSoon }">
            <Icon name="clock" :size="11" />{{ file.expires_at ? new Date(file.expires_at).toLocaleDateString() : 'Permanent' }}
          </span>
          <span v-if="file.has_password" class="chip" title="Password protected">
            <Icon name="lock" :size="11" />Protected
          </span>
        </div>
      </div>
      <div class="file-actions">
        <template v-if="file.has_password">
          <input
            v-model="password"
            type="password"
            placeholder="Password"
            class="unlock-input"
            :aria-label="`Password for ${file.original_filename}`"
            data-testid="file-unlock-input"
            @keyup.enter="handleUnlock"
          />
          <button
            type="button"
            class="btn-unlock"
            data-testid="file-unlock-button"
            :disabled="loading"
            @click="handleUnlock"
          >
            {{ loading ? 'Unlocking…' : 'Unlock' }}
          </button>
        </template>
        <a v-else :href="filesApi.fileUrl(file.short_code)" target="_blank" rel="noopener noreferrer" class="btn-open">
          <Icon name="download" :size="12" />Open
        </a>
        <button class="btn-delete" @click="emit('delete', file.id)">Delete</button>
      </div>
    </div>
    <p v-if="error" class="error file-unlock-error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.file-card {
  background: var(--color-background-soft);
  padding: 0.9rem 1.1rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  margin-bottom: 0.6rem;
  transition: background 0.35s ease, border-color 0.2s ease;
}

.file-card:hover {
  border-color: var(--color-border-hover);
}

.file-card-main {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.file-icon {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  background: var(--color-accent-soft);
  color: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  display: block;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-heading);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.3rem;
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

.file-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.btn-open {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-accent);
  background: transparent;
  color: var(--color-accent);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.82rem;
  text-decoration: none;
  transition: background 0.2s;
}

.btn-open:hover {
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

.btn-open:focus-visible,
.btn-delete:focus-visible,
.btn-unlock:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.unlock-input {
  padding: 0.35rem 0.5rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  font-size: 0.82rem;
  width: 8rem;
}

.unlock-input:focus {
  outline: none;
  border-color: var(--color-accent);
}

.btn-unlock {
  padding: 0.35rem 0.75rem;
  border: 1px solid var(--color-accent);
  background: transparent;
  color: var(--color-accent);
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.82rem;
  transition: background 0.2s;
}

.btn-unlock:hover:not(:disabled) {
  background: var(--color-accent-soft);
}

.btn-unlock:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.file-unlock-error {
  margin: 0.5rem 0 0;
  font-size: 0.82rem;
}

@media (max-width: 640px) {
  .file-card-main {
    flex-wrap: wrap;
  }

  .file-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
