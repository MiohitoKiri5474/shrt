<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'
import Icon, { type IconName } from './AppIcon.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const pageTitle = computed(() => (route.meta.title as string | undefined) ?? '')
const showDrawer = ref(false)

interface NavItem {
  name: string
  to: string
  label: string
  icon: IconName
}

const navItems = computed(() => {
  const items: NavItem[] = [
    { name: 'manage', to: '/manage', label: 'Manage', icon: 'link' },
    { name: 'new-link', to: '/new', label: 'New link', icon: 'plus' },
    { name: 'profile', to: '/profile', label: 'Profile', icon: 'user' },
  ]
  if (authStore.user?.is_admin) {
    items.push({ name: 'admin', to: '/admin', label: 'Admin', icon: 'shield' })
  }
  return items
})

function openDrawer() {
  showDrawer.value = true
}

function closeDrawer() {
  showDrawer.value = false
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') closeDrawer()
}

watch(showDrawer, (open) => {
  if (open) {
    document.addEventListener('keydown', handleKeydown)
  } else {
    document.removeEventListener('keydown', handleKeydown)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
})

async function handleSignOut() {
  closeDrawer()
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <header class="navbar" :class="{ 'navbar--rail': authStore.isAuthenticated }">
    <RouterLink to="/" class="navbar-brand">
      <span class="brand-mark" aria-hidden="true" />
      Shrt
    </RouterLink>
    <h1 class="navbar-title">{{ pageTitle }}</h1>

    <nav v-if="authStore.isAuthenticated" class="rail-nav" aria-label="Primary">
      <RouterLink
        v-for="item in navItems"
        :key="item.name"
        :to="item.to"
        class="rail-item"
        :class="{ 'rail-item--active': route.name === item.name }"
      >
        <Icon :name="item.icon" :size="16" />
        {{ item.label }}
      </RouterLink>
    </nav>

    <div class="navbar-actions">
      <slot name="status" />
      <button
        class="theme-toggle"
        :aria-label="themeStore.isDark ? '昼モードに切り替え' : '夜モードに切り替え'"
        :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
        @click="themeStore.toggle()"
      >
        <Icon :name="themeStore.isDark ? 'sun' : 'moon'" :size="14" />
      </button>
      <button
        v-if="authStore.isAuthenticated"
        class="hamburger-btn"
        :aria-expanded="showDrawer"
        aria-haspopup="dialog"
        :aria-label="showDrawer ? 'Close menu' : 'Open menu'"
        @click="openDrawer"
      >
        <span class="bar" />
        <span class="bar" />
        <span class="bar" />
      </button>
    </div>
  </header>

  <Teleport to="body">
    <div v-if="showDrawer" class="drawer-backdrop" @click="closeDrawer">
      <aside
        class="drawer-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Navigation menu"
        @click.stop
      >
        <div class="drawer-header">
          <span class="drawer-user">{{ authStore.user?.username ?? authStore.user?.email }}</span>
          <button class="drawer-close" aria-label="Close menu" @click="closeDrawer">
            <Icon name="x" :size="15" />
          </button>
        </div>
        <hr class="drawer-sep" />
        <nav class="drawer-links">
          <RouterLink
            v-if="route.name !== 'manage'"
            class="drawer-item"
            to="/manage"
            @click="closeDrawer"
          >Manage</RouterLink>
          <RouterLink
            v-if="route.name !== 'new-link'"
            class="drawer-item"
            to="/new"
            @click="closeDrawer"
          >New Link</RouterLink>
          <RouterLink
            v-if="route.name !== 'profile'"
            class="drawer-item"
            to="/profile"
            @click="closeDrawer"
          >Profile</RouterLink>
          <RouterLink
            v-if="authStore.user?.is_admin && route.name !== 'admin'"
            class="drawer-item"
            to="/admin"
            @click="closeDrawer"
          >Admin</RouterLink>
        </nav>
        <hr class="drawer-sep" />
        <button class="drawer-item drawer-item--danger" @click="handleSignOut">Sign out</button>
      </aside>
    </div>
  </Teleport>
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
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--color-heading);
  letter-spacing: 0.02em;
  text-decoration: none;
}

.brand-mark {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  background: var(--color-accent);
  flex-shrink: 0;
}

.navbar-title {
  justify-self: center;
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading);
}

.rail-nav {
  display: none;
}

.rail-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.55rem 0.65rem;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  color: var(--color-text);
  opacity: 0.75;
  text-decoration: none;
  border-left: 2px solid transparent;
  transition: background 0.15s, opacity 0.15s;
}

.rail-item:hover {
  opacity: 1;
  background: var(--color-background-mute);
}

.rail-item:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}

.rail-item--active {
  opacity: 1;
  color: var(--color-accent);
  background: var(--color-accent-soft);
  border-left-color: var(--color-accent);
  font-weight: 500;
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

.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 200;
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: min(300px, 85vw);
  height: 100%;
  background: var(--color-background-soft);
  border-left: 1px solid var(--color-border);
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  padding: 1rem;
  animation: drawer-slide-in 0.2s ease-out;
}

@keyframes drawer-slide-in {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .drawer-panel {
    animation: none;
  }
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.drawer-user {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  opacity: 0.85;
  font-weight: 500;
  color: var(--color-text);
}

.drawer-close {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--color-text);
  padding: 0.25rem;
  display: flex;
}

.drawer-close:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.drawer-sep {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: 0.75rem 0;
}

.drawer-links {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.drawer-item {
  display: block;
  width: 100%;
  padding: 0.6rem 0.75rem;
  font-size: 0.9rem;
  color: var(--color-text);
  text-decoration: none;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
}

.drawer-item:hover {
  background: var(--color-background-mute);
}

.drawer-item:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}

.drawer-item--danger {
  color: var(--color-error);
}

/* Desktop: authenticated pages get a persistent left rail instead of a top bar.
   Below the breakpoint (and on any unauthenticated page) this stays the original
   top bar + hamburger drawer. */
@media (min-width: 880px) {
  .navbar--rail {
    grid-template-columns: none;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    width: var(--sidebar-width);
    min-width: var(--sidebar-width);
    height: 100vh;
    position: sticky;
    top: 0;
    padding: 1.25rem 0.9rem;
    border-bottom: none;
    border-right: 1px solid var(--color-border);
    gap: 0.25rem;
  }

  .navbar--rail .navbar-brand {
    padding: 0 0.4rem;
    margin-bottom: 1.25rem;
  }

  /* Hidden from view (the rail nav already labels the current page), but
     kept in the a11y tree — this is the page's only h1. */
  .navbar--rail .navbar-title {
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

  .navbar--rail .rail-nav {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .navbar--rail .navbar-actions {
    margin-top: auto;
    justify-self: auto;
    padding-top: 0.75rem;
    border-top: 1px solid var(--color-border);
  }

  .navbar--rail .hamburger-btn {
    display: none;
  }
}
</style>
