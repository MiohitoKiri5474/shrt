<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'

const route = useRoute()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const pageTitle = computed(() => (route.meta.title as string | undefined) ?? '')
</script>

<template>
  <header class="navbar">
    <RouterLink to="/" class="navbar-brand">Shrt</RouterLink>
    <h1 class="navbar-title">{{ pageTitle }}</h1>
    <div class="navbar-actions">
      <slot name="status" />
      <button
        class="theme-toggle"
        :aria-label="themeStore.isDark ? '昼モードに切り替え' : '夜モードに切り替え'"
        :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
        @click="themeStore.toggle()"
      >
        <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
      </button>
      <button
        v-if="authStore.isAuthenticated"
        class="hamburger-btn"
        aria-haspopup="dialog"
        aria-label="Open menu"
      >
        <span class="bar" />
        <span class="bar" />
        <span class="bar" />
      </button>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0.75rem 2rem;
  background: var(--color-background-soft);
  border-bottom: 1px solid var(--color-border);
  transition: background 0.35s ease, border-color 0.35s ease;
}

.navbar-brand {
  justify-self: start;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--color-heading);
  letter-spacing: 0.02em;
  text-decoration: none;
}

.navbar-title {
  justify-self: center;
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading);
}

.navbar-actions {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.theme-toggle {
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, border-color 0.2s, transform 0.2s;
  color: var(--color-text);
  padding: 0;
}

.theme-toggle:hover {
  background: var(--color-border);
  transform: rotate(15deg);
}

.theme-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.hamburger-btn {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  width: 2.1rem;
  height: 2.1rem;
  padding: 0.35rem;
  background: transparent;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.hamburger-btn:hover {
  background: var(--color-border);
}

.hamburger-btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.bar {
  display: block;
  width: 100%;
  height: 2px;
  background: var(--color-text);
  border-radius: 2px;
}
</style>
