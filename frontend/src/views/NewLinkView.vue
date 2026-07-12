<script setup lang="ts">
import AppNavbar from '../components/AppNavbar.vue'
import CreateURLForm from '../components/CreateURLForm.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'
</script>

<template>
  <div class="new-link">
    <AppNavbar>
      <template #status>
        <NetworkStatusIndicator />
      </template>
    </AppNavbar>
    <main class="new-link-content">
      <CreateURLForm />
    </main>
  </div>
</template>

<style scoped>
.new-link {
  min-height: 100vh;
  background: var(--color-background);
}

.new-link-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1rem;
}
</style>
