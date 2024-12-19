<script setup lang="ts">
import {
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
  type VisibilityState,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useVueTable,
} from '@tanstack/vue-table'
import type { Alert } from '~/composables/useAlerts'
import AlertStatisticsChart from './AlertStatisticsChart.vue'

interface Props {
  columns: ColumnDef<Alert, any>[]
  data: Alert[]
  page?: number
  pageSize?: number
  totalItems?: number
  totalPages?: number
  sorting?: SortingState
  loading?: boolean
  onPageChange?: (page: number) => void
  onPageSizeChange?: (size: number) => void
}

const props = withDefaults(defineProps<Props>(), {
  page: 1,
  pageSize: 20,
  totalItems: 0,
  totalPages: 1,
  sorting: () => [],
  loading: false,
  onPageChange: undefined,
  onPageSizeChange: undefined,
})

const emit = defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [size: number]
  'update:sorting': [sorting: SortingState]
  'update:rowSelection': [selection: Record<string, boolean>]
}>()

const sorting = ref<SortingState>(props.sorting)
const columnFilters = ref<ColumnFiltersState>([])
const columnVisibility = ref<VisibilityState>({})
const rowSelection = ref<Record<string, boolean>>({})

// Generate a unique key for each row using page number, row index, and alert_id
const rowKey = (row: any, index: number) => `${props.page}-${index}-${row.original.alert_id}`

const table = useVueTable({
  get data() {
    return props.data
  },
  get columns() {
    return props.columns
  },
  state: {
    get sorting() {
      return sorting.value
    },
    get columnFilters() {
      return columnFilters.value
    },
    get columnVisibility() {
      return columnVisibility.value
    },
    get rowSelection() {
      return rowSelection.value
    },
  },
  onSortingChange: (updater) => {
    const newValue = typeof updater === 'function' ? updater(sorting.value) : updater
    sorting.value = newValue
    emit('update:sorting', newValue)
  },
  onColumnFiltersChange: (updater) => {
    columnFilters.value = typeof updater === 'function' ? updater(columnFilters.value) : updater
  },
  onColumnVisibilityChange: (updater) => {
    columnVisibility.value = typeof updater === 'function' ? updater(columnVisibility.value) : updater
  },
  onRowSelectionChange: (updater) => {
    const newValue = typeof updater === 'function' ? updater(rowSelection.value) : updater
    rowSelection.value = newValue
    emit('update:rowSelection', newValue)
  },
  getCoreRowModel: getCoreRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  getSortedRowModel: getSortedRowModel(),
  manualPagination: true,
  pageCount: props.totalPages,
  enableRowSelection: true,
  enableMultiRowSelection: true,
  getRowId: (row: Alert, index: number) => `${props.page}-${index}-${row.alert_id}`,
})

const handlePageChange = (page: number) => {
  emit('update:page', page)
  if (props.onPageChange) {
    props.onPageChange(page)
  }
}

const handlePageSizeChange = (size: number) => {
  emit('update:pageSize', size)
  if (props.onPageSizeChange) {
    props.onPageSizeChange(size)
  }
}

// Watch for external sorting changes
watch(() => props.sorting, (newSorting) => {
  if (JSON.stringify(newSorting) !== JSON.stringify(sorting.value)) {
    sorting.value = newSorting
  }
}, { deep: true })

// Clear row selection when page changes
watch(() => props.page, () => {
  rowSelection.value = {}
})

// Watch for data changes to update row selection
watch(() => props.data, () => {
  // Remove selection for rows that no longer exist
  const validIds = new Set(props.data.map((row, index) => `${props.page}-${index}-${row.alert_id}`))
  for (const id of Object.keys(rowSelection.value)) {
    if (!validIds.has(id)) {
      delete rowSelection.value[id]
    }
  }
}, { deep: true })
</script>

<template>
  <div class="w-full space-y-4 overflow-x-auto">
    <!-- Add Statistics Chart -->
    <AlertStatisticsChart :time-range="24" />
    
    <DataTableToolbar :table="table" />
    <div class="relative min-w-full border rounded-md">
      <!-- Loading Overlay -->
      <div
        v-if="loading"
        class="absolute inset-0 z-50 flex items-center justify-center bg-background/50 backdrop-blur-sm"
      >
        <div class="flex items-center space-x-4">
          <Spinner class="w-6 h-6" />
          <p class="text-sm text-muted-foreground">Loading data...</p>
        </div>
      </div>

      <Table>
        <TableHeader>
          <TableRow v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
            <TableHead 
              v-for="header in headerGroup.headers" 
              :key="header.id"
              :class="[
                header.column.columnDef.id === 'select' ? 'w-[48px] p-0' : '',
              ]"
            >
              <template v-if="!header.isPlaceholder">
                <component
                  :is="header.column.columnDef.header"
                  :column="header.column"
                  :table="table"
                  :header="header"
                />
              </template>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow
            v-for="(row, index) in table.getRowModel().rows"
            :key="rowKey(row, index)"
            :data-state="row.getIsSelected() && 'selected'"
            class="[&>td]:py-3 data-[state=selected]:bg-muted/50"
          >
            <TableCell 
              v-for="cell in row.getVisibleCells()" 
              :key="cell.id"
              :class="[
                cell.column.columnDef.id === 'select' ? 'w-[48px] p-0' : '',
              ]"
            >
              <component
                :is="cell.column.columnDef.cell"
                :cell="cell"
                :column="cell.column"
                :getValue="cell.getValue"
                :renderValue="cell.renderValue"
                :table="table"
                :row="row"
              />
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
    <DataTablePagination
      :current-page="page"
      :page-size="pageSize"
      :total-items="totalItems"
      :total-pages="totalPages"
      :selected-rows="Object.keys(rowSelection).length"
      @update:page="handlePageChange"
      @update:page-size="handlePageSizeChange"
    />
  </div>
</template>
