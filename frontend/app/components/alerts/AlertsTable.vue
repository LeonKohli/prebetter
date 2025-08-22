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
// Vue imports are auto-imported by Nuxt
import { useIntervalFn, useDocumentVisibility, watchDebounced } from '@vueuse/core'
import { valueUpdater } from '@/utils/utils'
import { applyDefaultDateFilters } from '@/utils/dateHelpers'
import type { AlertListItem, GroupedAlert, FlattenedGroupedAlert, AlertListResponse, GroupedAlertResponse, PaginatedResponse } from '@/types/alerts'

// URL state synchronization with proper browser navigation
const router = useRouter()
const route = useRoute()
const urlState = useNavigableUrlState({
  defaultView: 'grouped',
  defaultPageSize: 100,
  defaultSortBy: 'detected_at',
  defaultSortOrder: 'desc',
  defaultGroupedSortBy: 'total_count',
  defaultUngroupedSortBy: 'detected_at'
})

// Track if we're changing views to show appropriate loading state
const isChangingView = ref(false)

// Handle navigation to filtered view when clicking on a classification
function handleViewAlertDetails(details: { sourceIp: string; targetIp: string; classification: string }) {
  // Mark as changing view
  isChangingView.value = true
  
  // Use navigateToDetails which properly creates a history entry
  urlState.navigateToDetails(details)
}

// Get column definitions from composable
const { groupedColumns, ungroupedColumns, sortFieldMap, filterFieldMap } = useAlertTableColumns()


// View mode directly from URL state
const isGrouped = computed(() => urlState.view.value === 'grouped')

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

// Compute the fetch URL dynamically based on isGrouped
const fetchUrl = computed(() => isGrouped.value ? '/api/alerts/groups' : '/api/alerts')

// Create a comprehensive key that includes ALL reactive state
const fetchKey = computed(() => {
  // Include all URL state that affects data fetching
  const stateHash = JSON.stringify({
    view: urlState.view.value,
    page: urlState.page.value,
    pageSize: urlState.pageSize.value,
    sortBy: urlState.sortBy.value,
    sortOrder: urlState.sortOrder.value,
    filters: urlState.filters.value,
    // Don't include hiddenColumns or autoRefresh as they don't affect data
  })
  return `alerts-${btoa(stateHash)}`
})

// Compute query parameters reactively
const fetchQuery = computed(() => {
  const mappedSortField = sortFieldMap[urlState.sortBy.value as keyof typeof sortFieldMap] || urlState.sortBy.value || 'detect_time'
  
  // Map filter fields
  const urlFilters = Object.fromEntries(
    Object.entries(urlState.filters.value).map(([key, value]) => [
      filterFieldMap[key as keyof typeof filterFieldMap] || key,
      value
    ])
  )
  
  // Apply today's date filter by default if no dates are specified
  const finalFilters = (!urlFilters.start_date && !urlFilters.end_date) 
    ? applyDefaultDateFilters(urlFilters)
    : urlFilters
  
  return {
    page: urlState.page.value,
    size: urlState.pageSize.value,
    sort_by: mappedSortField,
    sort_order: urlState.sortOrder.value,
    ...finalFilters
  }
})

// Use useFetch with a dynamic key to prevent NS_BINDING_ABORTED
// This creates separate fetch instances for different states
const { data, pending, error, refresh, status, execute } = await useFetch<GroupedAlertResponse | AlertListResponse>(
  fetchUrl,
  {
    key: fetchKey, // Dynamic key prevents request cancellation
    query: fetchQuery,
    server: true,
    lazy: false,
    dedupe: 'defer', // Defer new requests until the previous one completes
    watch: false // Disable automatic watching - we'll handle it manually
  }
)

// Don't show error when data is being fetched (status is 'pending')
const displayError = computed(() => {
  // Only show errors when we're not actively fetching
  if (status.value === 'pending' || !error.value) return null
  return error.value
})

// Auto-refresh configuration
const autoRefreshInterval = computed(() => urlState.autoRefresh.value * 1000) // Convert to milliseconds
const autoRefreshEnabled = computed(() => urlState.autoRefresh.value > 0)

// Track if current refresh is auto-refresh (silent)
const isSilentRefresh = ref(false)

// Simple loading state - show overlay only for user actions
const showLoadingOverlay = computed(() => 
  status.value === 'pending' && data.value !== undefined && !isSilentRefresh.value
)

// No need for type guards - we control the response type based on isGrouped

// Current columns based on view mode
const columns = computed(() => isGrouped.value ? groupedColumns : ungroupedColumns)

// Extract data and pagination from response
const displayData = computed(() => {
  if (!data.value) return []
  
  if (isGrouped.value) {
    // We know it's GroupedAlertResponse based on the fetch URL
    const response = data.value as GroupedAlertResponse
    const flattenedAlerts: FlattenedGroupedAlert[] = []
    
    response.groups?.forEach((group, groupIndex) => {
      if (group.alerts && group.alerts.length > 0) {
        const sortedAlerts = [...group.alerts].sort((a, b) => b.count - a.count)
        
        sortedAlerts.forEach((alert, alertIndex) => {
          flattenedAlerts.push({
            source_ipv4: group.source_ipv4,
            target_ipv4: group.target_ipv4,
            total_count: group.total_count,
            classification: alert.classification,
            count: alert.count,
            analyzer: alert.analyzer,
            analyzer_host: alert.analyzer_host,
            detected_at: alert.detected_at,
            groupIndex: groupIndex,
            alertIndex: alertIndex,
            isFirstInGroup: alertIndex === 0,
            isLastInGroup: alertIndex === sortedAlerts.length - 1,
            groupSize: sortedAlerts.length
          })
        })
      }
    })
    
    return flattenedAlerts
  } else {
    // We know it's AlertListResponse based on the fetch URL
    const response = data.value as AlertListResponse
    return response.items || []
  }
})

const paginationInfo = computed((): PaginatedResponse => {
  if (!data.value) return { total: 0, pages: 0, page: 1, size: 100 }
  
  if (isGrouped.value) {
    const response = data.value as GroupedAlertResponse
    return response.pagination || { total: 0, pages: 0, page: 1, size: 100 }
  } else {
    const response = data.value as AlertListResponse
    return response.pagination || { total: 0, pages: 0, page: 1, size: 100 }
  }
})

// Define table data type - includes flattened grouped alerts
type TableDataItem = FlattenedGroupedAlert | AlertListItem;

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
      return `${row.source_ipv4 || 'unknown'}-${row.target_ipv4 || 'unknown'}-${row.classification || 'unknown'}-${row.groupIndex}-${row.alertIndex}`
    } else if ('id' in row) {
      return row.id
    }
    return 'unknown'
  },
})

// Toggle view function
const handleToggleView = () => {
  const newView = urlState.view.value === 'grouped' ? 'ungrouped' : 'grouped'
  
  // Set flag to show skeleton
  isChangingView.value = true
  
  // Clear selection
  rowSelection.value = {}
  
  const newQuery: Record<string, any> = {
    ...route.query,
    view: newView
  }
  
  // Remove sort to use view-specific defaults
  delete newQuery.sort
  
  // Reset to page 1 when switching views
  if (urlState.page.value !== 1) {
    newQuery.page = '1'
  }
  
  // Remove classification filter when switching to grouped
  if (newView === 'grouped' && urlState.filters.value.classification_text) {
    const currentFilters = { ...urlState.filters.value }
    delete currentFilters.classification_text
    newQuery.filter = Object.keys(currentFilters).length > 0 ? JSON.stringify(currentFilters) : undefined
  }
  
  router.push({ query: newQuery })
}

// Auto-refresh functionality using VueUse
const performAutoRefresh = async () => {
  // Skip if already loading or user has active selections
  if (status.value === 'pending' || Object.keys(rowSelection.value).length > 0) return
  
  try {
    isSilentRefresh.value = true
    await refresh()
  } catch (error) {
    console.error('Auto-refresh failed:', error)
  } finally {
    isSilentRefresh.value = false
  }
}

// Declarative auto-refresh with useIntervalFn
const { pause: stopAutoRefresh, resume: startAutoRefresh, isActive: isAutoRefreshActive } = useIntervalFn(
  performAutoRefresh,
  autoRefreshInterval,
  { 
    immediate: false,
    immediateCallback: false 
  }
)

// Use watchDebounced to handle key changes with a small delay
// This prevents rapid request triggering when multiple state values change
watchDebounced(
  fetchKey,
  () => {
    execute()
  },
  { debounce: 50 } // Small debounce to batch multiple state changes
)

// Remove unnecessary watcher - status already tracks this

// Reset view changing flag when data loads
watch(status, (newStatus) => {
  if (newStatus === 'success' || newStatus === 'error') {
    isChangingView.value = false
  }
})

// Watch for auto-refresh enable/disable
watch(autoRefreshEnabled, (enabled) => {
  if (enabled) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})

// Document visibility handling - only on client to avoid SSR issues
const documentVisibility = process.client ? useDocumentVisibility() : ref('visible')

// Watch document visibility and handle auto-refresh - only on client
if (process.client) {
  watch(documentVisibility, async (visibility) => {
    if (visibility === 'hidden') {
      stopAutoRefresh()
    } else if (visibility === 'visible' && autoRefreshEnabled.value) {
      startAutoRefresh()
      // Refresh immediately when coming back to tab
      await performAutoRefresh()
    }
  })
}

// Provide context for child components
provideAlertTableContext({
  urlState,
  table,
  isGrouped,
  pending
})

// Start auto-refresh on mount
onMounted(() => {
  if (autoRefreshEnabled.value) {
    startAutoRefresh()
  }
})

// Cleanup on unmount
onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<template>
  <div class="w-full h-full flex flex-col space-y-2">
    <!-- Toolbar -->
    <AlertsToolbar
      @toggleView="handleToggleView"
      @startAutoRefresh="startAutoRefresh"
      @stopAutoRefresh="stopAutoRefresh"
    />

    <!-- Table with Brandenburg-style design -->
    <div 
      class="flex-1 min-h-0 rounded-lg bg-card shadow-sm table-scroll-container relative overflow-hidden"
    >
      <Table class="table-compact table-inner-borders table-zebra" role="table" aria-label="Security alerts table">
        <TableHeader class="sticky top-0 z-10 bg-muted">
          <TableRow v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id" class="h-10">
            <TableHead v-for="header in headerGroup.headers" :key="header.id" class="py-2 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              <FlexRender v-if="!header.isPlaceholder" :render="header.column.columnDef.header" :props="header.getContext()" />
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody class="relative">
          <!-- Loading overlay - show when loading after initial load -->
          <Transition name="fade">
            <div 
              v-if="showLoadingOverlay" 
              class="absolute inset-0 bg-background/40 z-10 pointer-events-none"
              role="status"
              aria-live="polite"
              aria-busy="true"
              aria-label="Loading alerts"
            />
          </Transition>
          
          <!-- Show skeleton on initial load or when changing views -->
          <template v-if="status === 'idle' || (status === 'pending' && !data) || isChangingView">
            <TableRow v-for="i in 20" :key="`skeleton-${i}`" class="h-11 border-0">
              <TableCell v-for="j in columns.length" :key="`skeleton-${i}-${j}`" class="py-2 px-4">
                <div class="h-4 bg-muted animate-pulse rounded" />
              </TableCell>
            </TableRow>
          </template>
          <!-- Show data when available -->
          <template v-else-if="table.getRowModel().rows?.length">
            <template v-for="row in table.getRowModel().rows" :key="row.id">
              <TableRow :data-state="row.getIsSelected() && 'selected'" class="h-11 border-0 hover:bg-muted/30 transition-colors duration-150">
                <TableCell v-for="cell in row.getVisibleCells()" :key="cell.id" class="py-2 px-4 text-sm font-normal">
                  <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
                </TableCell>
              </TableRow>
            </template>
          </template>
          <!-- Empty state - only show when not changing views, not loading, and truly no data -->
          <TableRow v-else-if="!isChangingView && status !== 'pending' && (status === 'success' || status === 'error')">
            <TableCell :colspan="columns.length" class="h-24 text-center">
              <div role="status" aria-live="polite">
                <span v-if="displayError">Error loading alerts. Please try again.</span>
                <span v-else>No alerts found.</span>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <!-- Brandenburg-style pagination -->
    <div class="flex items-center justify-between h-12 px-4 border-t border-border bg-muted/20">
      <div class="flex items-center gap-4">
        <div class="text-sm text-muted-foreground">
          <template v-if="!isGrouped && table.getFilteredSelectedRowModel().rows.length > 0">
            {{ table.getFilteredSelectedRowModel().rows.length }} of
          </template>
          {{ paginationInfo.total }} {{ isGrouped ? 'groups' : 'alerts' }}
        </div>
        
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
        
        <div class="flex items-center gap-1">
          <span class="text-sm">
            Page {{ urlState.page.value }} of {{ paginationInfo.pages || 1 }}
          </span>
        </div>
        
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
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>