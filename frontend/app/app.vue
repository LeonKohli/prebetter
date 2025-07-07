<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup lang="ts">
// Global app configuration
useHead({
  titleTemplate: (titleChunk) => {
    return titleChunk ? `${titleChunk} - Prebetter SIEM` : 'Prebetter SIEM';
  }
})

// Set auth-ready state to prevent login flash
const { ready } = useUserSession()

// Initialize as not ready
if (process.client) {
  document.documentElement.dataset.authReady = 'false'
}

// Watch for auth ready state
watch(ready, (val) => {
  if (process.client && val) {
    document.documentElement.dataset.authReady = 'true'
  }
}, { immediate: true })
</script>

<style>

</style>
