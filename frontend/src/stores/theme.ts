import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const stored = localStorage.getItem('theme')
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const isDark = ref(stored === 'dark' || (!stored && prefersDark))

  function toggle() {
    isDark.value = !isDark.value
  }

  watch(
    isDark,
    (dark) => {
      localStorage.setItem('theme', dark ? 'dark' : 'light')
      document.documentElement.classList.toggle('dark', dark)
    },
    { immediate: true, flush: 'sync' },
  )

  return { isDark, toggle }
})
