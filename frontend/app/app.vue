<template>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
</template>

<script setup lang="ts">
// Get auth session state
const { ready } = useUserSession()

// Global app configuration with reactive HTML attributes
useHead({
  titleTemplate: (titleChunk) => {
    return titleChunk ? `${titleChunk} - Prebetter SIEM` : 'Prebetter SIEM';
  },
  htmlAttrs: {
    lang: 'de-DE',
    'data-auth-ready': () => String(ready.value)
  }
})
</script>

<style>

</style>
