<template>
  <div class="min-h-screen flex flex-col bg-background text-foreground transition-colors duration-300">
    <Navbar />

    <main class="flex-1" role="main">
      <slot />
    </main>

    <footer role="contentinfo" class="py-6 px-4 text-center text-xs text-muted-foreground border-t">
      <p>&copy; {{ new Date().getFullYear() }} Prebetter SIEM Dashboard. All rights reserved.</p>
      <p class="mt-2 text-xs text-muted-foreground">
        Security Information and Event Management System
      </p>
    </footer>
  </div>
</template>

<script setup lang="ts">
// Basic SEO meta tags for the layout
useSeoMeta({
  title: 'Prebetter SIEM Dashboard',
  ogTitle: 'Prebetter SIEM Dashboard',
  description: 'A modern Security Information and Event Management dashboard for Prelude IDS',
  ogDescription: 'A modern Security Information and Event Management dashboard for Prelude IDS',
})

// Define Schema.org structured data
useSchemaOrg([
  defineWebSite({
    name: 'Prebetter SIEM Dashboard',
    description: 'A modern Security Information and Event Management dashboard for Prelude IDS',
  }),
])
</script>
