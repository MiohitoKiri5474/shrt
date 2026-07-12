import { ref, readonly, type Ref } from 'vue'

const COPY_STATUS_RESET_MS = 1500

export interface ClipboardCopy {
  /** True for COPY_STATUS_RESET_MS after a successful copy. */
  copied: Readonly<Ref<boolean>>
  /** True for COPY_STATUS_RESET_MS after a failed copy attempt. */
  copyError: Readonly<Ref<boolean>>
  /** Copy `text` to the clipboard, falling back to `execCommand('copy')` when the async Clipboard API is unavailable. */
  copy: (text: string) => Promise<void>
}

/**
 * Copies text to the clipboard using the async Clipboard API when available,
 * falling back to the legacy `document.execCommand('copy')` approach otherwise
 * (e.g. insecure contexts or older browsers). `execCommand`'s return value is
 * checked explicitly — it resolves/returns without throwing even when the copy
 * silently fails, so a `false` result is treated as an error too.
 *
 * Exposes `copied`/`copyError` flags that flip back to `false`
 * COPY_STATUS_RESET_MS after they're set, so calling UI can show transient
 * "Copied!" / "Failed!" status text.
 */
export function useClipboardCopy(): ClipboardCopy {
  const copied = ref(false)
  const copyError = ref(false)

  async function copy(text: string): Promise<void> {
    copyError.value = false
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(text)
      } else {
        const el = document.createElement('textarea')
        el.value = text
        el.style.cssText = 'position:fixed;opacity:0'
        document.body.appendChild(el)
        el.select()
        const succeeded = document.execCommand('copy')
        document.body.removeChild(el)
        if (!succeeded) {
          throw new Error('execCommand copy failed')
        }
      }
      copied.value = true
      setTimeout(() => { copied.value = false }, COPY_STATUS_RESET_MS)
    } catch {
      copyError.value = true
      setTimeout(() => { copyError.value = false }, COPY_STATUS_RESET_MS)
    }
  }

  return {
    copied: readonly(copied),
    copyError: readonly(copyError),
    copy,
  }
}
