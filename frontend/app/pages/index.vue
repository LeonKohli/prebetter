<script setup lang="ts">
import type { ColumnDef } from '@tanstack/vue-table'
import type { Alert } from '~/composables/useAlerts'
import type { SortingState } from '@tanstack/vue-table'
import { columns } from '~/composables/columns'

const { alerts, pending, error, filters, total, totalPages, setPage, setPageSize, setSorting } = useAlerts()

// Initialize with empty sorting state
const sorting = ref<SortingState>([])

const handleSortingChange = (newSorting: SortingState) => {
  sorting.value = newSorting
  if (newSorting.length > 0) {
    const { id, desc } = newSorting[0]
    let sortField = id
    // Map column IDs to API sort fields
    if (id === 'classification_text') sortField = 'classification'
    else if (id === 'source_ipv4') sortField = 'source_ip'
    else if (id === 'target_ipv4') sortField = 'target_ip'
    // analyzer.name is now handled by the explicit column id
    
    setSorting(sortField as 'detect_time' | 'create_time' | 'severity' | 'classification' | 'source_ip' | 'target_ip' | 'analyzer', desc ? 'desc' : 'asc')
  } else {
    setSorting(undefined, undefined)
  }
}

useHead({
  title: 'Security Alerts Dashboard',
  meta: [
    {
      name: 'description',
      content: 'View and manage security alerts for your organization',
    },
  ],
})
</script>

<template>
  <div class="container-fluid px-4 sm:px-6 lg:px-8 py-10 mx-auto max-w-[2000px]">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold tracking-tight">
          Security Alerts
        </h1>
        <p class="text-muted-foreground">
          View and manage security alerts for your organization
        </p>
      </div>
    </div>
    <div v-if="error" class="mt-8">
      <Alert variant="destructive">
        <Icon name="lucide:alert-circle" class="w-4 h-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>
          {{ error.message }}
        </AlertDescription>
      </Alert>
    </div>
    <div class="mt-8">
      <DataTable
        :columns="columns"
        :data="alerts || []"
        :loading="pending"
        :page="filters.page"
        :page-size="filters.size"
        :total-items="total"
        :total-pages="totalPages"
        :sorting="sorting"
        @update:page="setPage"
        @update:page-size="setPageSize"
        @update:sorting="handleSortingChange"
      />
    </div>
  </div>
</template>