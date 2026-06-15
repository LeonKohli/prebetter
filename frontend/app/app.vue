<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup lang="ts">
// Get auth session state
const { isPending } = useAuth()

// Global app configuration with reactive HTML attributes
useHead({
  titleTemplate: (titleChunk) => {
    return titleChunk ? `${titleChunk} - Prebetter IDS` : 'Prebetter IDS';
  },
  htmlAttrs: {
    lang: 'de-DE',
    'data-auth-ready': () => String(!isPending.value)
  }
})
</script>
