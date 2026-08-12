<script setup lang="ts">
import { useRoute } from 'vue-router'
import Icon from '../components/Icon.vue'

const route = useRoute()
const code = route.query.code as string | undefined
</script>

<template>
  <main class="expired-container">
    <div class="expired-card">
      <Icon name="clock" :size="28" class="expired-icon" />
      <h1>Link Expired</h1>
      <p class="expired-subtitle">
        This short link has expired and is no longer available.
      </p>
      <p v-if="code" class="expired-code">Code: <code>{{ code }}</code></p>
      <a href="/" class="btn-home">Go to homepage</a>
    </div>
  </main>
</template>

<style scoped>
.expired-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 1rem;
  background: var(--color-background);
}

.expired-card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 2rem 2.5rem;
  max-width: 400px;
  width: 100%;
  text-align: center;
}

.expired-icon {
  color: var(--color-warning);
  margin-bottom: 0.75rem;
}

h1 {
  font-size: 1.5rem;
  color: var(--color-heading);
  margin-bottom: 0.5rem;
}

.expired-subtitle {
  color: var(--color-text);
  opacity: 0.7;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.expired-code {
  font-size: 0.85rem;
  color: var(--color-text);
  opacity: 0.6;
  margin-bottom: 1.5rem;
}

.expired-code code {
  background: var(--color-background);
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-family: monospace;
}

.btn-home {
  display: inline-block;
  padding: 0.65rem 1.5rem;
  background: var(--color-accent);
  color: var(--color-background);
  border-radius: var(--radius-md);
  text-decoration: none;
  font-weight: 500;
  font-size: 1rem;
  transition: opacity 0.2s;
}

.btn-home:hover {
  opacity: 0.88;
}
</style>
