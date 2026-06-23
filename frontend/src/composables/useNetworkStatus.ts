import { computed, onMounted, onUnmounted, readonly, ref, type Ref } from 'vue'
import { healthApi } from '../api/health'

const DEFAULT_POLL_INTERVAL_MS = 30_000

export interface NetworkStatus {
  /** True while the backend last responded healthily. */
  isOnline: Readonly<Ref<boolean>>
  /** True when connectivity is lost and the banner has not been dismissed. */
  showBanner: Readonly<Ref<boolean>>
  /** Hide the offline banner until connectivity drops again. */
  dismissBanner: () => void
  /** Force an immediate connectivity check (used by tests and event handlers). */
  check: () => Promise<void>
}

/**
 * Tracks backend reachability by polling `/api/health` on an interval and by
 * reacting to the browser's own online/offline events for instant feedback.
 *
 * Connectivity is treated as "online" only when the health endpoint answers
 * with `status: "ok"`. Any rejection — network error, timeout, or non-2xx
 * (e.g. a 502 when the backend container is down) — counts as "offline".
 */
export function useNetworkStatus(intervalMs: number = DEFAULT_POLL_INTERVAL_MS): NetworkStatus {
  const isOnline = ref(true)
  const bannerDismissed = ref(false)
  let timer: ReturnType<typeof setInterval> | undefined

  async function check(): Promise<void> {
    try {
      const { status } = await healthApi.check()
      setOnline(status === 'ok')
    } catch {
      setOnline(false)
    }
  }

  function setOnline(online: boolean): void {
    // Recovering from an outage resets the dismissal so a future drop shows
    // the banner again instead of staying silently hidden.
    if (online && !isOnline.value) {
      bannerDismissed.value = false
    }
    isOnline.value = online
  }

  function dismissBanner(): void {
    bannerDismissed.value = true
  }

  const showBanner = computed(() => !isOnline.value && !bannerDismissed.value)

  // The browser knows about hard network loss before the next poll fires.
  function handleBrowserOffline(): void {
    setOnline(false)
  }
  function handleBrowserOnline(): void {
    void check()
  }

  onMounted(() => {
    void check()
    timer = setInterval(() => void check(), intervalMs)
    window.addEventListener('online', handleBrowserOnline)
    window.addEventListener('offline', handleBrowserOffline)
  })

  onUnmounted(() => {
    if (timer !== undefined) {
      clearInterval(timer)
    }
    window.removeEventListener('online', handleBrowserOnline)
    window.removeEventListener('offline', handleBrowserOffline)
  })

  return {
    isOnline: readonly(isOnline),
    showBanner: readonly(showBanner),
    dismissBanner,
    check,
  }
}
