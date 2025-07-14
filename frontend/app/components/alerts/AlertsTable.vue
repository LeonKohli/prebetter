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
import { Users, List } from 'lucide-vue-next'
import { ref, computed, watch, shallowRef, onMounted, onUnmounted } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { valueUpdater } from '@/utils/utils'
import type { AlertListItem, GroupedAlert, AlertListResponse, GroupedAlertResponse, PaginatedResponse } from '@/types/alerts'

// Get column definitions from composable
const { groupedColumns, ungroupedColumns, sortFieldMap, filterFieldMap } = useAlertTableColumns()

// View mode toggle
const isGrouped = ref(true)

// Table state
const sorting = ref<SortingState>([{ id: 'detected_at', desc: true }])
const columnFilters = ref<ColumnFiltersState>([])
const columnVisibility = ref<VisibilityState>({})
const rowSelection = ref({})
const pagination = ref({ pageIndex: 0, pageSize: 100 }) // Max allowed by backend


// Abort controller for cancelling requests
let abortController: AbortController | null = null

// Data fetching for grouped view
const { data: groupedData, pending: groupedPending, refresh: refreshGrouped, error: groupedError } = await useFetch<GroupedAlertResponse>('/api/alerts/groups', {
  query: computed(() => {
    // Only fetch if this is the active view
    if (!isGrouped.value) return null
    
    const sortField = sorting.value[0]?.id
    const mappedSortField = sortField ? (sortFieldMap[sortField as keyof typeof sortFieldMap] || sortField) : 'detect_time'
    
    const filters = Object.fromEntries(
      columnFilters.value.map(f => [filterFieldMap[f.id as keyof typeof filterFieldMap] || f.id, f.value])
    )
    
    return {
      page: pagination.value.pageIndex + 1,
      size: pagination.value.pageSize,
      sort_by: mappedSortField,
      sort_order: sorting.value[0]?.desc ? 'desc' : 'asc',
      ...filters
    }
  }),
  server: true,  // Enable SSR for SEO and initial load
  lazy: true,    // Don't block navigation
  immediate: true,
  getCachedData(key) {
    // Return cached data if less than 30 seconds old
    const nuxtApp = useNuxtApp()
    const cached = nuxtApp.payload.data[key] || nuxtApp.static.data[key]
    if (cached && cached.fetchedAt && Date.now() - cached.fetchedAt < 30000) {
      return cached
    }
  },
  watch: false  // Manual control for better performance
})

// Data fetching for ungrouped view
const { data: ungroupedData, pending: ungroupedPending, refresh: refreshUngrouped, error: ungroupedError } = await useFetch<AlertListResponse>('/api/alerts', {
  query: computed(() => {
    // Only fetch if this is the active view
    if (isGrouped.value) return null
    
    const sortField = sorting.value[0]?.id
    const mappedSortField = sortField ? (sortFieldMap[sortField as keyof typeof sortFieldMap] || sortField) : 'detect_time'
    
    const filters = Object.fromEntries(
      columnFilters.value.map(f => [filterFieldMap[f.id as keyof typeof filterFieldMap] || f.id, f.value])
    )
    
    return {
      page: pagination.value.pageIndex + 1,
      size: pagination.value.pageSize,
      sort_by: mappedSortField,
      sort_order: sorting.value[0]?.desc ? 'desc' : 'asc',
      ...filters
    }
  }),
  server: true,  // Enable SSR
  lazy: true,
  immediate: false,  // Don't fetch immediately since it's not the default view
  getCachedData(key) {
    const nuxtApp = useNuxtApp()
    const cached = nuxtApp.payload.data[key] || nuxtApp.static.data[key]
    if (cached && cached.fetchedAt && Date.now() - cached.fetchedAt < 30000) {
      return cached
    }
  },
  watch: false
})

// Reactive data for table with caching
type TableDataItem = GroupedAlert | AlertListItem;
const tableData = shallowRef<TableDataItem[]>([])
const previousTableData = shallowRef<TableDataItem[]>([])
const isInitialLoad = ref(true)
const dataTransitionTimeout = ref<number | null>(null)
const isSwitchingView = ref(false)

// Auto-refresh configuration
const AUTO_REFRESH_INTERVAL = 30000 // 30 seconds
const autoRefreshEnabled = ref(true)
const refreshTimer = ref<NodeJS.Timeout | null>(null)
const isUserInteracting = ref(false)
const interactionTimeout = ref<NodeJS.Timeout | null>(null)
const isSilentRefresh = ref(false)

// Animation state - only enable after hydration
const isAnimationReady = ref(false)

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

// Update table data when view mode or data changes
watch([isGrouped, groupedData, ungroupedData], () => {
  // Clear switching flag when new data arrives
  isSwitchingView.value = false
  
  if (isGrouped.value && groupedData.value && isGroupedResponse(groupedData.value)) {
    const newData = groupedData.value.groups || []
    if (newData.length > 0) {
      previousTableData.value = tableData.value
      tableData.value = newData
      isInitialLoad.value = false
      
      // Clear previous data after transition completes
      if (dataTransitionTimeout.value) {
        clearTimeout(dataTransitionTimeout.value)
      }
      dataTransitionTimeout.value = setTimeout(() => {
        previousTableData.value = []
      }, 500) as unknown as number
    }
  } else if (!isGrouped.value && ungroupedData.value && isAlertListResponse(ungroupedData.value)) {
    const newData = ungroupedData.value.items || []
    if (newData.length > 0) {
      previousTableData.value = tableData.value
      tableData.value = newData
      isInitialLoad.value = false
      
      // Clear previous data after transition
      if (dataTransitionTimeout.value) {
        clearTimeout(dataTransitionTimeout.value)
      }
      dataTransitionTimeout.value = setTimeout(() => {
        previousTableData.value = []
      }, 500) as unknown as number
    }
  }
}, { immediate: true })

// Current columns based on view mode
const columns = computed(() => isGrouped.value ? groupedColumns : ungroupedColumns)

// Pagination info
const paginationInfo = computed((): PaginatedResponse => {
  if (isGrouped.value && groupedData.value && isGroupedResponse(groupedData.value)) {
    return groupedData.value.pagination || { total: 0, pages: 0, page: 1, size: 100 }
  } else if (!isGrouped.value && ungroupedData.value && isAlertListResponse(ungroupedData.value)) {
    return ungroupedData.value.pagination || { total: 0, pages: 0, page: 1, size: 100 }
  }
  return { total: 0, pages: 0, page: 1, size: 100 }
})

// Loading and error states
const pending = computed(() => {
  // During SSR, always return false to prevent hydration mismatches
  if (import.meta.server) return false
  return isGrouped.value ? groupedPending.value : ungroupedPending.value
})
const error = computed(() => isGrouped.value ? groupedError.value : ungroupedError.value)

// Display data - use previous data while loading new data
const displayData = computed(() => {
  // During view switch, show empty to trigger loading state immediately
  if (isSwitchingView.value) {
    return []
  }
  
  // If we have current data, use it
  if (tableData.value.length > 0) {
    return tableData.value
  }
  // If loading and we have previous data, keep showing it
  if (pending.value && previousTableData.value.length > 0) {
    return previousTableData.value
  }
  // Otherwise return empty array
  return []
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

// Create table instance
const table = useVueTable({
  get data() { return displayData.value },
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

// Toggle view function
async function toggleView() {
  // Don't switch if currently loading
  if (pending.value) return
  
  // Set switching flag
  isSwitchingView.value = true
  
  // Clear current data to prevent flash
  tableData.value = []
  previousTableData.value = []
  
  isGrouped.value = !isGrouped.value
  // Reset pagination when switching views
  pagination.value.pageIndex = 0
  // Clear selection
  rowSelection.value = {}
  
  // Stop auto-refresh during switch
  stopAutoRefresh()
  
  try {
    // Trigger the appropriate fetch
    if (isGrouped.value) {
      await refreshGrouped()
    } else {
      await refreshUngrouped()
    }
  } finally {
    isSwitchingView.value = false
    // Restart auto-refresh
    startAutoRefresh()
  }
}

// Debounced refresh function
const debouncedRefresh = useDebounceFn(async () => {
  // Cancel any pending requests
  if (abortController) {
    abortController.abort()
  }
  
  // Create new abort controller
  abortController = new AbortController()
  
  try {
    if (isGrouped.value) {
      await refreshGrouped()
    } else {
      await refreshUngrouped()
    }
  } catch (error: any) {
    if (error.name !== 'AbortError') {
      console.error('Failed to refresh data:', error)
    }
  }
}, 300)

// Watch for pagination changes
watch(() => pagination.value.pageIndex, () => {
  debouncedRefresh()
})

watch(() => pagination.value.pageSize, () => {
  pagination.value.pageIndex = 0  // Reset to first page
  debouncedRefresh()
})

// Watch for sorting/filter changes
watch([sorting, columnFilters], () => {
  pagination.value.pageIndex = 0
  debouncedRefresh()
}, { deep: true })

// Auto-refresh functions
const performSilentRefresh = async () => {
  // Skip if user is interacting or data is loading
  if (isUserInteracting.value || pending.value) {
    return
  }
  
  // Skip if user has active selections
  if (Object.keys(rowSelection.value).length > 0) {
    return
  }
  
  // Mark as silent refresh
  isSilentRefresh.value = true
  
  // Perform the refresh
  try {
    if (isGrouped.value) {
      await refreshGrouped()
    } else {
      await refreshUngrouped()
    }
  } catch (error) {
    console.error('Auto-refresh failed:', error)
  } finally {
    // Reset flag after a short delay to ensure UI has updated
    setTimeout(() => {
      isSilentRefresh.value = false
    }, 100)
  }
}

const startAutoRefresh = () => {
  stopAutoRefresh() // Clear any existing timer
  
  if (autoRefreshEnabled.value) {
    refreshTimer.value = setInterval(performSilentRefresh, AUTO_REFRESH_INTERVAL)
  }
}

const stopAutoRefresh = () => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
    refreshTimer.value = null
  }
}

// User interaction detection
const handleUserInteraction = () => {
  isUserInteracting.value = true
  
  // Clear existing timeout
  if (interactionTimeout.value) {
    clearTimeout(interactionTimeout.value)
  }
  
  // Reset after 3 seconds of no interaction
  interactionTimeout.value = setTimeout(() => {
    isUserInteracting.value = false
  }, 3000)
}

// Start auto-refresh on mount
onMounted(() => {
  // Enable animations after hydration
  isAnimationReady.value = true
  
  startAutoRefresh()
  
  // Pause when tab is hidden
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

const handleVisibilityChange = async () => {
  if (document.hidden) {
    stopAutoRefresh()
  } else if (autoRefreshEnabled.value) {
    startAutoRefresh()
    // Refresh immediately when coming back to tab
    await performSilentRefresh()
  }
}

// Cleanup on unmount
onUnmounted(() => {
  stopAutoRefresh()
  if (abortController) {
    abortController.abort()
  }
  if (dataTransitionTimeout.value) {
    clearTimeout(dataTransitionTimeout.value)
  }
  if (interactionTimeout.value) {
    clearTimeout(interactionTimeout.value)
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <div class="w-full h-full flex flex-col space-y-2">
    <!-- Compact header with filters and view toggle -->
    <div class="flex items-center justify-between pb-2">
      <div class="flex items-center gap-3">
        <div class="relative">
          <Icon name="lucide:search" class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            class="h-9 w-72 pl-9 pr-3 border-border bg-background/50 focus:bg-background transition-colors"
            placeholder="Filter alerts by classification..."
            :model-value="(columnFilters.find(f => f.id === 'classification_text')?.value as string) || ''"
            @update:model-value="(value) => {
              const existing = columnFilters.findIndex(f => f.id === 'classification_text')
              if (value) {
                if (existing >= 0) {
                  const filter = columnFilters[existing]
                  if (filter) {
                    filter.value = value
                  }
                } else {
                  columnFilters.push({ id: 'classification_text', value })
                }
              } else if (existing >= 0) {
                columnFilters.splice(existing, 1)
              }
            }"
          />
        </div>
      </div>
      
      <div class="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          @click="async () => {
            autoRefreshEnabled = !autoRefreshEnabled
            if (autoRefreshEnabled) {
              startAutoRefresh()
              await performSilentRefresh() // Refresh immediately
            } else {
              stopAutoRefresh()
            }
          }"
          class="h-8 w-8"
          :title="autoRefreshEnabled ? 'Disable auto-refresh' : 'Enable auto-refresh'"
        >
          <Icon 
            :name="autoRefreshEnabled ? 'lucide:refresh-cw' : 'lucide:refresh-cw-off'" 
            :class="[
              'h-4 w-4',
              !autoRefreshEnabled && 'text-muted-foreground',
              isAnimationReady && pending && autoRefreshEnabled && 'animate-spin'
            ]"
          />
        </Button>
        
        <Button
          variant="outline"
          size="sm"
          @click="toggleView"
          class="h-8 px-3 text-xs font-medium border-border hover:bg-background transition-all"
          :disabled="isSwitchingView || pending"
        >
          <Users v-if="!isGrouped" class="mr-2 h-3.5 w-3.5" />
          <List v-else class="mr-2 h-3.5 w-3.5" />
          {{ isGrouped ? 'Show Individual' : 'Group by IP' }}
        </Button>
        
        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button variant="outline" size="sm" class="h-8 px-3 text-xs font-medium border-border hover:bg-background">
              <Icon name="lucide:columns" class="mr-2 h-3.5 w-3.5" />
              Columns <Icon name="lucide:chevron-down" class="ml-1 h-3 w-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuCheckboxItem
              v-for="column in table.getAllColumns().filter((column) => column.getCanHide())"
              :key="column.id"
              class="capitalize"
              :model-value="column.getIsVisible()"
              @update:model-value="(value) => column.toggleVisibility(!!value)"
            >
              {{ column.id }}
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>

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
          v-if="pending && !isInitialLoad && !isSilentRefresh" 
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
            <!-- Initial loading state with skeleton -->
            <template v-if="isInitialLoad && pending">
              <TableRow v-for="i in 10" :key="`skeleton-${i}`" class="h-11 border-b border-border">
                <TableCell v-for="j in columns.length" :key="`skeleton-${i}-${j}`" class="py-2 px-4">
                  <div class="h-4 bg-muted animate-pulse rounded" />
                </TableCell>
              </TableRow>
            </template>
            <!-- Show data -->
            <template v-else-if="table.getRowModel().rows?.length">
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
              <!-- Server-side render skeleton -->
              <TableRow v-for="i in 10" :key="`ssr-skeleton-${i}`" class="h-11 border-b border-border">
                <TableCell v-for="j in columns.length" :key="`ssr-skeleton-${i}-${j}`" class="py-2 px-4">
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
        <div class="text-sm text-muted-foreground">
          <template v-if="!isGrouped && table.getFilteredSelectedRowModel().rows.length > 0">
            {{ table.getFilteredSelectedRowModel().rows.length }} of
          </template>
          {{ paginationInfo.total }} {{ isGrouped ? 'groups' : 'alerts' }}
        </div>
        
        <div class="flex items-center gap-2">
          <span class="text-sm text-muted-foreground">Show</span>
          <Select
            :model-value="pagination.pageSize.toString()"
            @update:model-value="(value) => {
              table.setPageSize(Number(value))
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
            :disabled="pagination.pageIndex === 0 || pending"
            @click="() => {
              pagination.pageIndex = Math.max(0, pagination.pageIndex - 1)
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
        
        <div class="flex items-center gap-1">
          <span class="text-sm">
            Page {{ pagination.pageIndex + 1 }} of {{ paginationInfo.pages || 1 }}
          </span>
        </div>
        
        <ClientOnly>
          <Button
            variant="outline"
            size="sm"
            :disabled="pagination.pageIndex >= (paginationInfo.pages - 1) || pending"
            @click="() => {
              pagination.pageIndex = Math.min(paginationInfo.pages - 1, pagination.pageIndex + 1)
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