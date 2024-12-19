<script setup lang="ts">
import type { ColumnDef } from '@tanstack/vue-table'
import type { Alert } from '~/composables/useAlerts'
import DataTableColumnHeader from '~/components/DataTableColumnHeader.vue'
import { Checkbox } from '@/components/ui/checkbox'
import type { SortingState } from '@tanstack/vue-table'

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

const columns: ColumnDef<Alert, any>[] = [
  {
    id: 'select',
    header: ({ table }) => h('div', { class: 'flex items-center justify-center h-4' }, [
      h(Checkbox, {
        checked: table.getIsAllRowsSelected(),
        'onUpdate:checked': (value: boolean) => table.toggleAllRowsSelected(!!value),
        'aria-label': 'Select all',
      }),
    ]),
    cell: ({ row }) => h('div', { class: 'flex items-center justify-center h-4' }, [
      h(Checkbox, {
        checked: row.getIsSelected(),
        'onUpdate:checked': (value: boolean) => row.toggleSelected(!!value),
        'aria-label': 'Select row',
      }),
    ]),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: 'severity',
    header: (props) => h(DataTableColumnHeader, { column: props.column, title: 'Severity' }),
    cell: ({ row }) => {
      const severity = row.getValue('severity') as string
      return h('div', { class: 'flex items-center' }, [
        h('div', {
          class: [
            'h-2 w-2 rounded-full mr-2',
            {
              'bg-red-500': severity === 'high',
              'bg-yellow-500': severity === 'medium',
              'bg-blue-500': severity === 'low',
            },
          ],
        }),
        severity,
      ])
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id))
    },
    enableSorting: true,
  },
  {
    accessorKey: 'detect_time',
    header: (props) => h(DataTableColumnHeader, { column: props.column, title: 'Detect Time' }),
    cell: ({ row }) => {
      const time = row.getValue('detect_time') as { time: string; usec: number; gmtoff: number }
      return h('div', {}, [
        new Date(time.time).toLocaleString()
      ])
    },
    enableSorting: true,
  },
  {
    accessorKey: 'classification_text',
    id: 'classification_text',
    header: (props) => h(DataTableColumnHeader, { column: props.column, title: 'Classification' }),
    enableSorting: true,
  },
  {
    accessorKey: 'source_ipv4',
    header: (props) => h(DataTableColumnHeader, { column: props.column, title: 'Source IP' }),
    enableSorting: true,
  },
  {
    accessorKey: 'target_ipv4',
    header: (props) => h(DataTableColumnHeader, { column: props.column, title: 'Target IP' }),
    enableSorting: true,
  },
  {
    accessorKey: 'analyzer.name',
    id: 'analyzer',
    header: (props) => h(DataTableColumnHeader, { column: props.column, title: 'Analyzer' }),
    enableSorting: true,
  },
]

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
  <div class="container py-10 mx-auto">
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
    <div v-if="pending" class="flex items-center justify-center mt-8">
      <div class="flex items-center space-x-4">
        <Spinner class="w-6 h-6" />
        <p class="text-muted-foreground">Loading alerts...</p>
      </div>
    </div>
    <div v-else-if="error" class="mt-8">
      <Alert variant="destructive">
        <Icon name="lucide:alert-circle" class="w-4 h-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>
          {{ error.message }}
        </AlertDescription>
      </Alert>
    </div>
    <div v-else-if="alerts" class="mt-8">
      <DataTable
        :columns="columns"
        :data="alerts"
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