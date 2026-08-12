<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useURLsStore } from '../stores/urls'
import { useFilesStore } from '../stores/files'
import { goToShare } from '../router/navigation'
import Icon from './Icon.vue'

const MAX_UPLOAD_BYTES = 25 * 1024 * 1024
const UPLOAD_LABEL: Record<'file' | 'image', string> = { file: 'File', image: 'Image' }
const UPLOAD_NOUN: Record<'file' | 'image', string> = { file: 'a file', image: 'an image' }

function uploadErrorMessage(kind: 'file' | 'image', status: number | undefined): string {
  if (status === 422) return `This ${kind} type is not allowed.`
  if (status === 413) {
    return kind === 'image' ? 'Image is too large or exceeds your 500MB image quota.' : 'File is too large.'
  }
  return `Failed to upload ${kind}.`
}

const router = useRouter()
const urlsStore = useURLsStore()
const filesStore = useFilesStore()
const uploadType = ref<'link' | 'file' | 'image'>('link')
const originalUrl = ref('')
const customCode = ref('')
const password = ref('')
const expiresAt = ref('')
const selectedFile = ref<File | null>(null)
const filePassword = ref('')
const error = ref('')
const loading = ref(false)
const showAdvanced = ref(false)

const submitLabel = computed(() => {
  if (uploadType.value === 'link') return loading.value ? 'Creating…' : 'Create short URL'
  return loading.value ? 'Uploading…' : `Upload ${UPLOAD_LABEL[uploadType.value].toLowerCase()}`
})

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

async function handleSubmit() {
  if (uploadType.value === 'file' || uploadType.value === 'image') {
    await handleUpload(uploadType.value)
  } else {
    await handleCreate()
  }
}

async function handleUpload(kind: 'file' | 'image') {
  error.value = ''
  if (!selectedFile.value) {
    error.value = `Please choose ${UPLOAD_NOUN[kind]} to upload.`
    return
  }
  if (selectedFile.value.size > MAX_UPLOAD_BYTES) {
    error.value = `${UPLOAD_LABEL[kind]} must be 25MB or smaller.`
    return
  }
  if (filePassword.value && filePassword.value.length < 6) {
    error.value = 'Password must be at least 6 characters.'
    return
  }
  loading.value = true
  try {
    await filesStore.upload(selectedFile.value, kind, filePassword.value || undefined)
    selectedFile.value = null
    filePassword.value = ''
    try {
      await router.push({ name: 'manage' })
    } catch (navError: unknown) {
      console.error(`Failed to navigate to the manage page after uploading ${kind}:`, navError)
      error.value = `Your ${kind} was uploaded, but we could not open the Manage page automatically.`
    }
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } }).response?.status
    error.value = uploadErrorMessage(kind, status)
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  error.value = ''
  if (originalUrl.value && !/^https?:\/\//i.test(originalUrl.value)) {
    originalUrl.value = 'https://' + originalUrl.value
  }
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
  if (customCode.value && !/^[A-Za-z0-9_-]{6,16}$/.test(customCode.value)) {
    error.value = 'Custom code must be 6–16 characters and contain only letters, digits, hyphens, or underscores.'
    return
  }
  if (password.value && password.value.length < 6) {
    error.value = 'Password must be at least 6 characters.'
    return
  }
  loading.value = true
  try {
    const created = await urlsStore.create(
      originalUrl.value,
      customCode.value || undefined,
      password.value || undefined,
      expiresAt.value ? new Date(expiresAt.value).toISOString() : undefined,
    )
    try {
      await goToShare(router, created.short_code)
    } catch (navError: unknown) {
      // The URL was already created successfully; a navigation failure here
      // (e.g. a lazy-chunk load error) is not a creation failure and must not
      // be reported as "Failed to create URL". Still, silently swallowing it
      // would leave the user staring at a form that looks untouched, with
      // every reason to resubmit and create a duplicate link.
      console.error('Failed to navigate to the share page after creating URL:', navError)
      error.value = 'Your link was created, but we could not open it automatically. Check the Manage page to find it.'
    }
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } }).response?.status
    if (status === 409) {
      error.value = 'Short code already taken.'
    } else {
      error.value = 'Failed to create URL.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="create-form" @submit.prevent="handleSubmit" data-testid="create-url-form">
    <h2>Share a link or a file</h2>

    <div class="field type-toggle" role="radiogroup" aria-label="What to share">
      <label :class="{ 'type-toggle-option--active': uploadType === 'link' }">
        <input type="radio" value="link" v-model="uploadType" />
        <Icon name="link" :size="14" />Link
      </label>
      <label :class="{ 'type-toggle-option--active': uploadType === 'file' }">
        <input type="radio" value="file" v-model="uploadType" />
        <Icon name="hash" :size="14" />File
      </label>
      <label :class="{ 'type-toggle-option--active': uploadType === 'image' }">
        <input type="radio" value="image" v-model="uploadType" />
        <Icon name="copy" :size="14" />Image
      </label>
    </div>

    <template v-if="uploadType === 'link'">
      <div class="field">
        <label for="original-url">Original URL</label>
        <div class="input-wrap">
          <Icon name="link" :size="14" />
          <input id="original-url" v-model="originalUrl" type="text" placeholder="example.com/your-long-link" required />
        </div>
      </div>

      <button type="button" class="advanced-toggle" :aria-expanded="showAdvanced" @click="showAdvanced = !showAdvanced">
        <Icon name="chevronDown" :size="14" />
        Advanced options
      </button>

      <div class="advanced-fields" v-show="showAdvanced">
        <div class="field">
          <label for="custom-code">Custom code</label>
          <div class="input-wrap">
            <Icon name="hash" :size="14" />
            <input id="custom-code" v-model="customCode" type="text" placeholder="my-link" maxlength="16" />
          </div>
        </div>
        <div class="field">
          <label for="link-password">Password protection</label>
          <div class="input-wrap">
            <Icon name="lock" :size="14" />
            <input id="link-password" v-model="password" type="password" placeholder="Leave blank for public link" maxlength="128" autocomplete="new-password" />
          </div>
        </div>
        <div class="field">
          <label for="expires-at">Expires at</label>
          <div class="input-wrap">
            <Icon name="calendar" :size="14" />
            <input id="expires-at" v-model="expiresAt" type="datetime-local" />
          </div>
        </div>
      </div>
    </template>

    <template v-else-if="uploadType === 'file'">
      <div class="field">
        <label for="upload-file">File (max 25MB, expires in 7 days)</label>
        <input id="upload-file" type="file" @change="handleFileChange" required />
      </div>
      <div class="field">
        <label for="file-password">Password protection (optional)</label>
        <div class="input-wrap">
          <Icon name="lock" :size="14" />
          <input id="file-password" v-model="filePassword" type="password" placeholder="Leave blank for public file" maxlength="128" autocomplete="new-password" />
        </div>
      </div>
    </template>

    <template v-else>
      <div class="field">
        <label for="upload-image">Image (max 25MB, never expires)</label>
        <input id="upload-image" type="file" accept="image/jpeg,image/png,image/gif,image/webp" @change="handleFileChange" required />
      </div>
    </template>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <button type="submit" class="btn-submit" :disabled="loading">{{ submitLabel }}</button>
  </form>
</template>

<style scoped>
.create-form {
  background: var(--color-background-soft);
  padding: 1.5rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  margin-bottom: 2rem;
  transition: background 0.35s ease;
}

h2 {
  margin-bottom: 1rem;
  font-size: 1.05rem;
  color: var(--color-heading);
}

.type-toggle {
  display: flex;
  gap: 0.35rem;
  padding: 0.25rem;
  margin-bottom: 1.25rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-background);
}

.type-toggle label {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  margin: 0;
  padding: 0.45rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text);
  opacity: 0.65;
  cursor: pointer;
  transition: background 0.2s, color 0.2s, opacity 0.2s;
}

.type-toggle label:hover {
  opacity: 0.9;
}

.type-toggle-option--active {
  background: var(--color-accent-soft);
  color: var(--color-accent);
  opacity: 1;
}

.type-toggle label:has(:focus-visible) {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.type-toggle input[type="radio"] {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.field {
  margin-bottom: 1rem;
}

.field label {
  display: block;
  margin-bottom: 0.3rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text);
}

.field input[type="file"] {
  display: block;
  width: 100%;
  padding: 0.5rem 0.6rem;
  border: 1px solid var(--color-border-hover);
  border-radius: var(--radius-md);
  background: var(--color-background);
  color: var(--color-text);
  font-size: 0.85rem;
  box-sizing: border-box;
}

.field input[type="file"]:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.55rem 0.7rem;
  border: 1px solid var(--color-border-hover);
  border-radius: var(--radius-md);
  background: var(--color-background);
  color: var(--color-text);
  opacity: 0.85;
  transition: background 0.35s ease, border-color 0.2s;
}

.input-wrap:focus-within {
  opacity: 1;
  border-color: var(--color-accent);
}

.input-wrap input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: var(--color-text);
  font-size: 0.9rem;
}

.advanced-toggle {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0 0 0.9rem;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--color-text);
  opacity: 0.65;
  font-size: 0.82rem;
  cursor: pointer;
}

.advanced-toggle:hover {
  opacity: 1;
}

.advanced-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.advanced-toggle :deep(svg) {
  transition: transform 0.15s ease;
}

.advanced-toggle[aria-expanded="true"] :deep(svg) {
  transform: rotate(180deg);
}

.btn-submit {
  padding: 0.6rem 1.2rem;
  background: var(--color-accent);
  color: var(--color-background);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: 500;
  transition: opacity 0.2s;
}

.btn-submit:hover:not(:disabled) {
  opacity: 0.88;
}

.btn-submit:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.btn-submit:disabled {
  opacity: 0.55;
}

.error {
  color: var(--color-error);
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}
</style>
