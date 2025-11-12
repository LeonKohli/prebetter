<template>
  <div class="min-h-screen flex flex-col bg-background text-foreground transition-colors duration-300">
    <Navbar />

    <main class="flex-1 overflow-hidden" role="main">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
useSeoMeta({
  title: 'Prebetter IDS Dashboard',
  ogTitle: 'Prebetter IDS Dashboard',
  description: 'A modern Intrusion Detection System dashboard for Prelude IDS',
  ogDescription: 'A modern Intrusion Detection System dashboard for Prelude IDS',
})

// See: https://schema.org/WebSite
useSchemaOrg([
  defineWebSite({
    name: 'Prebetter IDS Dashboard',
    description: 'A modern Intrusion Detection System dashboard for Prelude IDS',
  }),
])
</script>
