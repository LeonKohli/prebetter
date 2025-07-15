<script setup lang="ts">
import type {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
} from '@tanstack/vue-table'
import {
  FlexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useVueTable,
} from '@tanstack/vue-table'
import { ref, computed, watch, shallowRef, onMounted, onUnmounted } from 'vue'
import type { Ref } from 'vue'
import type { DropdownMenuCheckboxItemProps } from 'reka-ui'
import { useDebounceFn, useIntervalFn, useTimeoutFn, useDocumentVisibility, useToggle } from '@vueuse/core'
import { valueUpdater } from '@/utils/utils'
import { applyDefaultDateFilters } from '@/utils/dateHelpers'
import type { AlertListItem, GroupedAlert, AlertListResponse, GroupedAlertResponse, PaginatedResponse } from '@/types/alerts'

// Get column definitions from composable
const { groupedColumns, ungroupedColumns, sortFieldMap, filterFieldMap } = useAlertTableColumns()

// URL state synchronization using VueUse Router
const urlState = useTableUrlState({
  defaultView: 'grouped',
  defaultPageSize: 100,
  defaultSortBy: 'detected_at',
  defaultSortOrder: 'desc'
})


// View mode from URL using VueUse toggle pattern
const [isGrouped, toggleView] = useToggle(urlState.view.value === 'grouped')

// Sync toggle state with URL
watch(isGrouped, (grouped) => {
  urlState.view.value = grouped ? 'grouped' : 'ungrouped'
})

// Sync URL changes back to toggle
watch(() => urlState.view.value, (view) => {
  const shouldBeGrouped = view === 'grouped'
  if (isGrouped.value !== shouldBeGrouped) {
    isGrouped.value = shouldBeGrouped
  }
})

// Table state synchronized with URL
const sorting = computed<SortingState>({
  get: () => urlState.toSortingState.value,
  set: (value) => urlState.fromSortingState(value)
})

const columnFilters = computed<ColumnFiltersState>({
  get: () => urlState.toFilterState.value,
  set: (value) => urlState.fromFilterState(value)
})

const columnVisibility = computed<VisibilityState>({
  get: () => urlState.toVisibilityState.value,
  set: (value) => urlState.fromVisibilityState(value)
})

const pagination = computed({
  get: () => urlState.toPaginationState.value,
  set: (value) => urlState.fromPaginationState(value.pageIndex, value.pageSize)
})

// Local state (not in URL)
const rowSelection = ref({})


// Single data fetch with reactive URL
const { data, pending, error, refresh } = await useFetch<GroupedAlertResponse | AlertListResponse>(() => {
  const endpoint = isGrouped.value ? '/api/alerts/groups' : '/api/alerts'
  return endpoint
}, {
  query: computed(() => {
    const mappedSortField = sortFieldMap[urlState.sortBy.value as keyof typeof sortFieldMap] || urlState.sortBy.value || 'detect_time'
    
    // Map filter fields
    const urlFilters = Object.fromEntries(
      Object.entries(urlState.filters.value).map(([key, value]) => [
        filterFieldMap[key as keyof typeof filterFieldMap] || key,
        value
      ])
    )
    
    // Apply defaults to filters
    const effectiveFilters = applyDefaultDateFilters(urlFilters)
    
    return {
      page: urlState.page.value,
      size: urlState.pageSize.value,
      sort_by: mappedSortField,
      sort_order: urlState.sortOrder.value,
      ...effectiveFilters
    }
  }),
  // Use a key that changes with both view and sort params to force refetch
  key: computed(() => `alerts-${isGrouped.value ? 'grouped' : 'ungrouped'}-${urlState.sortBy.value}-${urlState.sortOrder.value}`),
  server: true,
  lazy: true,
  dedupe: 'cancel'
})

// Auto-refresh configuration
const autoRefreshInterval = computed(() => urlState.autoRefresh.value * 1000) // Convert to milliseconds
const autoRefreshEnabled = computed(() => urlState.autoRefresh.value > 0)

// User interaction state
const isUserInteracting = ref(false)
const { start: startInteractionTimeout, stop: stopInteractionTimeout } = useTimeoutFn(
  () => { isUserInteracting.value = false },
  3000,
  { immediate: false }
)

// Animation state - only enable after hydration
const isAnimationReady = ref(false)

// All available columns
const allColumns = ['source_ipv4', 'target_ipv4', 'detected_at', 'severity', 'classification_text', 'analyzer', 'total_count'] as const

// Declarative column visibility refs
type Checked = DropdownMenuCheckboxItemProps['modelValue']

// Create computed refs for each column that sync with URL state
const columnRefs: Record<string, Ref<Checked>> = {}

// Initialize computed refs for each column
allColumns.forEach(colId => {
  columnRefs[colId] = computed<Checked>({
    get: () => columnVisibility.value[colId] !== false,
    set: (value) => {
      const newVisibility = { ...columnVisibility.value }
      if (value) {
        newVisibility[colId] = true
      } else {
        newVisibility[colId] = false
      }
      columnVisibility.value = newVisibility
    }
  })
})



// Type guards for safe data access
function isGroupedResponse(data: unknown): data is GroupedAlertResponse {
  return data !== null && 
         typeof data === 'object' && 
         'groups' in data &&
         Array.isArray((data as any).groups);
}

function isAlertListResponse(data: unknown): data is AlertListResponse {
  return data !== null && 
         typeof data === 'object' && 
         'items' in data &&
         Array.isArray((data as any).items);
}

// Current columns based on view mode
const columns = computed(() => isGrouped.value ? groupedColumns : ungroupedColumns)

// Extract data and pagination from response
const displayData = computed(() => {
  if (!data.value) return []
  
  if (isGrouped.value && isGroupedResponse(data.value)) {
    return data.value.groups || []
  } else if (!isGrouped.value && isAlertListResponse(data.value)) {
    return data.value.items || []
  }
  return []
})

const paginationInfo = computed((): PaginatedResponse => {
  if (!data.value) return { total: 0, pages: 0, page: 1, size: 100 }
  
  if (isGrouped.value && isGroupedResponse(data.value)) {
    return data.value.pagination || { total: 0, pages: 0, page: 1, size: 100 }
  } else if (!isGrouped.value && isAlertListResponse(data.value)) {
    return data.value.pagination || { total: 0, pages: 0, page: 1, size: 100 }
  }
  return { total: 0, pages: 0, page: 1, size: 100 }
})

// Handle errors
watch(error, (newError) => {
  if (newError) {
    // 401 errors are handled globally by api-guard plugin
    // Only log non-401 errors
    if (newError.statusCode !== 401) {
      console.error('Failed to fetch alerts:', newError)
    }
  }
})

// Define table data type
type TableDataItem = GroupedAlert | AlertListItem;

// Create table instance
const table = useVueTable({
  get data() { return displayData.value as TableDataItem[] },
  get columns() { return columns.value as ColumnDef<TableDataItem>[] },
  getCoreRowModel: getCoreRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  onSortingChange: updaterOrValue => valueUpdater(updaterOrValue, sorting),
  onColumnFiltersChange: updaterOrValue => valueUpdater(updaterOrValue, columnFilters),
  onColumnVisibilityChange: updaterOrValue => valueUpdater(updaterOrValue, columnVisibility),
  onRowSelectionChange: updaterOrValue => valueUpdater(updaterOrValue, rowSelection),
  onPaginationChange: updaterOrValue => valueUpdater(updaterOrValue, pagination),
  manualPagination: true,
  manualSorting: true,
  manualFiltering: true,
  get pageCount() { return paginationInfo.value.pages || 1 },
  state: {
    get sorting() { return sorting.value },
    get columnFilters() { return columnFilters.value },
    get columnVisibility() { return columnVisibility.value },
    get rowSelection() { return rowSelection.value },
    get pagination() { return pagination.value },
  },
  getRowId: (row) => {
    if (isGrouped.value && 'total_count' in row) {
      return `${row.source_ipv4 || 'unknown'}-${row.target_ipv4 || 'unknown'}`
    } else if ('id' in row) {
      return row.id
    }
    return 'unknown'
  },
})

// Enhanced toggle view function with VueUse pattern
function handleToggleView() {
  // Use VueUse toggle
  toggleView()
  
  // Reset page and selection
  urlState.page.value = 1
  rowSelection.value = {}
  urlState.hiddenColumns.value = []
  
  // Get available columns for the new view
  const newColumns = columns.value.map(c => c.id || (c as any).accessorKey).filter(Boolean)
  
  // Check if current sort field exists in new view
  if (!newColumns.includes(urlState.sortBy.value)) {
    // Reset to a safe default that exists in both views
    urlState.sortBy.value = 'source_ipv4'
    urlState.sortOrder.value = 'desc'
  }
}

// Auto-refresh functionality using VueUse
const performSilentRefresh = async () => {
  // Skip if user is interacting or data is loading
  if (isUserInteracting.value || pending.value) return
  
  // Skip if user has active selections
  if (Object.keys(rowSelection.value).length > 0) return
  
  try {
    await refresh()
  } catch (error) {
    console.error('Auto-refresh failed:', error)
  }
}

// Declarative auto-refresh with useIntervalFn
const { pause: stopAutoRefresh, resume: startAutoRefresh, isActive: isAutoRefreshActive } = useIntervalFn(
  performSilentRefresh,
  autoRefreshInterval,
  { 
    immediate: false,
    immediateCallback: false 
  }
)

// Watch for auto-refresh enable/disable
watch(autoRefreshEnabled, (enabled) => {
  if (enabled) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})

// User interaction detection
const handleUserInteraction = () => {
  isUserInteracting.value = true
  stopInteractionTimeout() // Clear existing timeout
  startInteractionTimeout() // Start new timeout
}

// Document visibility handling
const documentVisibility = useDocumentVisibility()

// Watch document visibility and handle auto-refresh
watch(documentVisibility, async (visibility) => {
  if (visibility === 'hidden') {
    stopAutoRefresh()
  } else if (visibility === 'visible' && autoRefreshEnabled.value) {
    startAutoRefresh()
    // Refresh immediately when coming back to tab
    await performSilentRefresh()
  }
})

// Start auto-refresh on mount
onMounted(() => {
  // Enable animations after hydration
  isAnimationReady.value = true
  
  if (autoRefreshEnabled.value) {
    startAutoRefresh()
  }
})

// Cleanup on unmount
onUnmounted(() => {
  stopAutoRefresh()
  stopInteractionTimeout()
})
</script>

<template>
  <div class="w-full h-full flex flex-col space-y-2">
    <!-- Toolbar -->
    <AlertsToolbar
      :urlState="urlState"
      :pending="pending"
      :isGrouped="isGrouped"
      :table="table"
      :columnRefs="columnRefs"
      @toggleView="handleToggleView"
      @startAutoRefresh="startAutoRefresh"
      @stopAutoRefresh="stopAutoRefresh"
    />

    <!-- Table with Brandenburg-style design -->
    <div 
      class="flex-1 min-h-0 rounded-lg border-2 border-border bg-card shadow-sm table-scroll-container relative"
      @mousedown="handleUserInteraction"
      @touchstart="handleUserInteraction"
      @keydown="handleUserInteraction"
      @wheel="handleUserInteraction"
    >
      <!-- Loading overlay - only show for user-initiated actions -->
      <Transition name="fade">
        <div 
          v-if="pending" 
          class="absolute inset-0 bg-background/50 backdrop-blur-sm z-20 flex items-center justify-center rounded-lg"
          role="status"
          aria-live="polite"
          aria-busy="true"
          aria-label="Loading alerts, please wait"
        >
          <div class="flex flex-col items-center gap-2">
            <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-primary" />
            <span class="text-sm text-muted-foreground">Loading alerts...</span>
          </div>
        </div>
      </Transition>
      
      <Table class="table-compact" role="table" aria-label="Security alerts table">
        <TableHeader class="sticky top-0 z-10 bg-muted/50 backdrop-blur-sm border-b-2 border-border">
          <TableRow v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id" class="h-10">
            <TableHead v-for="header in headerGroup.headers" :key="header.id" class="py-2 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              <FlexRender v-if="!header.isPlaceholder" :render="header.column.columnDef.header" :props="header.getContext()" />
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <ClientOnly>
            <!-- Show data -->
            <template v-if="table.getRowModel().rows?.length">
              <template v-for="row in table.getRowModel().rows" :key="row.id">
                <TableRow :data-state="row.getIsSelected() && 'selected'" class="h-11 border-b border-border hover:bg-muted/30 transition-colors duration-150">
                  <TableCell v-for="cell in row.getVisibleCells()" :key="cell.id" class="py-2 px-4 text-sm font-normal">
                    <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
                  </TableCell>
                </TableRow>
              </template>
            </template>
            <!-- Empty state only when not loading and no data -->
            <TableRow v-else-if="!pending">
              <TableCell :colspan="columns.length" class="h-24 text-center">
                <div role="status" aria-live="polite">
                  <span v-if="error">Error loading alerts. Please try again.</span>
                  <span v-else>No alerts found.</span>
                </div>
              </TableCell>
            </TableRow>
            <template #fallback>
              <!-- Loading skeleton -->
              <TableRow v-for="i in 5" :key="`skeleton-${i}`" class="h-11 border-b border-border">
                <TableCell v-for="j in columns.length" :key="`skeleton-${i}-${j}`" class="py-2 px-4">
                  <div class="h-4 bg-muted animate-pulse rounded" />
                </TableCell>
              </TableRow>
            </template>
          </ClientOnly>
        </TableBody>
      </Table>
    </div>

    <!-- Brandenburg-style pagination -->
    <div class="flex items-center justify-between h-12 px-4 border-t border-border bg-muted/20">
      <div class="flex items-center gap-4">
        <ClientOnly>
          <div class="text-sm text-muted-foreground">
            <template v-if="!isGrouped && table.getFilteredSelectedRowModel().rows.length > 0">
              {{ table.getFilteredSelectedRowModel().rows.length }} of
            </template>
            {{ paginationInfo.total }} {{ isGrouped ? 'groups' : 'alerts' }}
          </div>
          <template #fallback>
            <div class="text-sm text-muted-foreground">
              Loading...
            </div>
          </template>
        </ClientOnly>
        
        <div class="flex items-center gap-2">
          <span class="text-sm text-muted-foreground">Show</span>
          <Select
            :model-value="urlState.pageSize.value.toString()"
            @update:model-value="(value) => {
              urlState.pageSize.value = Number(value)
            }"
          >
            <SelectTrigger class="h-8 w-[70px] text-xs border-border">
              <SelectValue placeholder="100" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10</SelectItem>
              <SelectItem value="20">20</SelectItem>
              <SelectItem value="50">50</SelectItem>
              <SelectItem value="100">100</SelectItem>
            </SelectContent>
          </Select>
          <span class="text-sm text-muted-foreground">per page</span>
        </div>
      </div>
      
      <div class="flex items-center space-x-2">
        <ClientOnly>
          <Button
            variant="outline"
            size="sm"
            :disabled="urlState.page.value === 1 || pending"
            @click="() => {
              urlState.page.value = Math.max(1, urlState.page.value - 1)
            }"
            class="h-8 px-3 text-xs font-medium border-border hover:bg-background disabled:opacity-50 transition-all"
          >
            <Icon name="lucide:chevron-left" class="mr-1 h-3.5 w-3.5" />
            Previous
          </Button>
          <template #fallback>
            <div class="h-8 w-20 bg-muted animate-pulse rounded"></div>
          </template>
        </ClientOnly>
        
        <ClientOnly>
          <div class="flex items-center gap-1">
            <span class="text-sm">
              Page {{ urlState.page.value }} of {{ paginationInfo.pages || 1 }}
            </span>
          </div>
          <template #fallback>
            <div class="flex items-center gap-1">
              <span class="text-sm">Page 1 of 1</span>
            </div>
          </template>
        </ClientOnly>
        
        <ClientOnly>
          <Button
            variant="outline"
            size="sm"
            :disabled="urlState.page.value >= paginationInfo.pages || pending"
            @click="() => {
              urlState.page.value = Math.min(paginationInfo.pages, urlState.page.value + 1)
            }"
            class="h-8 px-3 text-xs font-medium border-border hover:bg-background disabled:opacity-50 transition-all"
          >
            Next
            <Icon name="lucide:chevron-right" class="ml-1 h-3.5 w-3.5" />
          </Button>
          <template #fallback>
            <div class="h-8 w-16 bg-muted animate-pulse rounded"></div>
          </template>
        </ClientOnly>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Make the Table component's internal container fill height */
.table-scroll-container {
  display: flex;
  flex-direction: column;
}

.table-scroll-container > div {
  height: 100%;
}

/* Fade transition for loading overlay */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>