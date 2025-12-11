<template>
  <div class="h-[calc(100vh-3rem)] px-2 md:px-4 pt-2 md:pt-4 pb-2 md:pb-4 flex flex-col gap-2">
    <!--
      ClientOnly with fallback keeps component tree consistent between SSR and client.
      Without fallback, .client.vue renders nothing on server, shifting component IDs
      and causing Reka UI hydration mismatches (v-0-3-X vs v-0-4-X).
    -->
    <ClientOnly>
      <AlertsTimeline class="shrink-0" />
      <template #fallback>
        <AlertsTimelineSkeleton class="shrink-0" />
      </template>
    </ClientOnly>
    <div class="flex-1 min-h-0">
      <AlertsTable />
    </div>
  </div>
</template>

<script setup lang="ts">
// AlertsTable is auto-imported by Nuxt
definePageMeta({
  requiresAuth: true,
})

useSeoMeta({
  title: 'Security Alerts - Prebetter IDS',
  description: 'Real-time security alert monitoring and analysis dashboard',
})
</script>