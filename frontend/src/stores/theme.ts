import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const stored = typeof localStorage !== 'undefined' ? localStorage.getItem('theme') : null
  const prefersDark = typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches
  const isDark = ref(stored === 'dark' || (!stored && prefersDark))

  function toggle() {
    isDark.value = !isDark.value
  }

  watch(
    isDark,
    (dark) => {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('theme', dark ? 'dark' : 'light')
      }
      if (typeof document !== 'undefined') {
        document.documentElement.classList.toggle('dark', dark)
      }
    },
    { immediate: true, flush: 'sync' },
  )

  return { isDark, toggle }
})
