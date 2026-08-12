<script setup lang="ts">
import Icon from '../components/Icon.vue'
</script>

<template>
  <main class="not-found-container">
    <div class="not-found-card">
      <Icon name="search" :size="28" class="not-found-icon" />
      <h1>Page not found</h1>
      <p class="not-found-subtitle">
        The page you're looking for doesn't exist or may have been moved.
      </p>
      <a href="/manage" class="btn-home">Back to Manage</a>
    </div>
  </main>
</template>

<style scoped>
.not-found-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 1rem;
  background: var(--color-background);
}

.not-found-card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 2rem 2.5rem;
  max-width: 400px;
  width: 100%;
  text-align: center;
}

.not-found-icon {
  color: var(--color-text);
  opacity: 0.5;
  margin-bottom: 0.75rem;
}

h1 {
  font-size: 1.5rem;
  color: var(--color-heading);
  margin-bottom: 0.5rem;
}

.not-found-subtitle {
  color: var(--color-text);
  opacity: 0.7;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
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
