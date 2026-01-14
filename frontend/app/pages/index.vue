<template>
  <div class="h-[calc(100vh-3rem)] px-2 md:px-4 pt-2 md:pt-4 pb-2 md:pb-4 flex flex-col gap-2">
    <!--
      ClientOnly with fallback keeps component tree consistent between SSR and client.
      Without fallback, .client.vue renders nothing on server, shifting component IDs
      and causing Reka UI hydration mismatches (v-0-3-X vs v-0-4-X).
    -->
    <ClientOnly>
      <AlertsTimeline :url-state="urlState" class="shrink-0" />
      <template #fallback>
        <AlertsTimelineSkeleton class="shrink-0" />
      </template>
    </ClientOnly>
    <AlertsTable :url-state="urlState" />
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  requiresAuth: true,
})

useSeoMeta({
  title: 'Security Alerts - Prebetter IDS',
  description: 'Real-time security alert monitoring and analysis dashboard',
})

// SINGLE source of truth for URL state - passed to both Timeline and Table
// This eliminates race conditions from multiple urlState instances
const urlState = useNavigableUrlState({
  defaultView: 'grouped',
  defaultPageSize: 100,
  defaultSortBy: 'detected_at',
  defaultSortOrder: 'desc',
  defaultGroupedSortBy: 'detected_at',
  defaultUngroupedSortBy: 'detected_at',
})
</script>