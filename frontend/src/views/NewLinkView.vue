<script setup lang="ts">
import AppNavbar from '../components/AppNavbar.vue'
import CreateURLForm from '../components/CreateURLForm.vue'
import NetworkStatusIndicator from '../components/NetworkStatusIndicator.vue'
</script>

<template>
  <div class="new-link app-shell">
    <AppNavbar>
      <template #status>
        <NetworkStatusIndicator />
      </template>
    </AppNavbar>
    <main class="new-link-content app-main">
      <CreateURLForm />
    </main>
  </div>
</template>

<style scoped>
.new-link-content {
  max-width: 480px;
  margin: 0 auto;
  padding: 2rem 1.5rem 3rem;
  width: 100%;
}
</style>
