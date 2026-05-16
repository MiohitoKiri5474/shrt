<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useThemeStore } from './stores/theme'

// Initialize theme store so the .dark class is applied before first render
useThemeStore()
</script>

<template>
  <RouterView />
</template>
