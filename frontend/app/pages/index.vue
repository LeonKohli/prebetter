<template>
  <div class="h-[calc(100vh-3rem)] px-2 md:px-4 pt-2 md:pt-4">
    <AlertsTable />
  </div>
</template>

<script setup lang="ts">
import AlertsTable from '@/components/AlertsTable.vue'

definePageMeta({
  requiresAuth: true,
})

useSeoMeta({
  title: 'Security Alerts - Prebetter IDS',
  description: 'Real-time security alert monitoring and analysis dashboard',
})
</script>