<script setup lang="ts">
import { computed } from 'vue'
import { useNetworkStatus } from '../composables/useNetworkStatus'

const { isOnline, showBanner, dismissBanner } = useNetworkStatus()

const label = computed(() => (isOnline.value ? 'Backend online' : 'Backend unreachable'))
</script>

<template>
  <span
    class="net-status"
    :class="{ 'is-offline': !isOnline }"
    role="status"
    aria-live="polite"
    :title="label"
  >
    <span class="net-dot" aria-hidden="true" />
    <span class="net-sr">{{ label }}</span>
  </span>

  <Teleport to="body">
    <div v-if="showBanner" class="net-banner" role="alert">
      <span class="net-banner-text">
        Connection to the server was lost. Retrying automatically&hellip;
      </span>
      <button type="button" class="net-banner-dismiss" aria-label="Dismiss" @click="dismissBanner">
        ✕
      </button>
    </div>
  </Teleport>
</template>

<style scoped>
.net-status {
  display: inline-flex;
  align-items: center;
}

.net-dot {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 50%;
  background: var(--color-success);
  box-shadow: 0 0 0 0 var(--color-success);
  animation: net-pulse 2.4s ease-out infinite;
}

.net-status.is-offline .net-dot {
  background: var(--color-error);
  box-shadow: 0 0 0 0 var(--color-error);
  animation: net-pulse-error 1.4s ease-out infinite;
}

/* Visually hidden but available to assistive tech. */
.net-sr {
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

@keyframes net-pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in oklch, var(--color-success) 55%, transparent);
  }
  70%,
  100% {
    box-shadow: 0 0 0 0.4rem transparent;
  }
}

@keyframes net-pulse-error {
  0% {
    box-shadow: 0 0 0 0 color-mix(in oklch, var(--color-error) 60%, transparent);
  }
  70%,
  100% {
    box-shadow: 0 0 0 0.45rem transparent;
  }
}

.net-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 0.6rem 1rem;
  background: var(--color-error);
  color: var(--color-background);
  font-size: 0.875rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}

.net-banner-text {
  font-weight: 500;
}

.net-banner-dismiss {
  position: absolute;
  right: 0.75rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.6rem;
  height: 1.6rem;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--color-background);
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.2s;
}

.net-banner-dismiss:hover {
  background: rgba(255, 255, 255, 0.2);
}

.net-banner-dismiss:focus-visible {
  outline: 2px solid var(--color-background);
  outline-offset: 1px;
}

@media (prefers-reduced-motion: reduce) {
  .net-dot,
  .net-status.is-offline .net-dot {
    animation: none;
  }
}
</style>
