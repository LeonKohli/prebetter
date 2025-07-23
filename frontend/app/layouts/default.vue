<template>
  <div class="min-h-screen flex flex-col bg-background text-foreground transition-colors duration-300">
    <Navbar />

    <main class="flex-1 overflow-hidden" role="main">
      <slot />
    </main>

    <footer role="contentinfo" class="fixed bottom-0 left-0 right-0 h-6 bg-background/80 backdrop-blur-sm border-t opacity-0 hover:opacity-100 transition-opacity duration-200 z-10">
      <div class="h-full flex items-center justify-center text-[10px] text-muted-foreground">
        <span>Prebetter SIEM &copy; {{ new Date().getFullYear() }}</span>
        <span class="mx-2">•</span>
        <ClientOnly>
          <span>{{ new Date().toLocaleTimeString() }}</span>
          <template #fallback>
            <span>--:--:--</span>
          </template>
        </ClientOnly>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
useSeoMeta({
  title: 'Prebetter SIEM Dashboard',
  ogTitle: 'Prebetter SIEM Dashboard',
  description: 'A modern Security Information and Event Management dashboard for Prelude IDS',
  ogDescription: 'A modern Security Information and Event Management dashboard for Prelude IDS',
})

// See: https://schema.org/WebSite
useSchemaOrg([
  defineWebSite({
    name: 'Prebetter SIEM Dashboard',
    description: 'A modern Security Information and Event Management dashboard for Prelude IDS',
  }),
])
</script>
