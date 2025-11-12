<script setup lang="ts">
import type {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  Table,
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
import { useIntervalFn, useDocumentVisibility, useEventListener, watchDebounced } from '@vueuse/core'
import { valueUpdater } from '@/utils/utils'
import type { AlertListItem, GroupedAlert, FlattenedGroupedAlert, CompactGroupedAlert, AlertListResponse, GroupedAlertResponse, PaginatedResponse } from '@/types/alerts'
import AlertDetailsDialog from '@/components/alerts/AlertDetailsDialog.vue'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import type { FetchError } from 'ofetch'
import { getPresetRange, isRelativePreset, isValidPresetId, type DatePresetId } from '@/utils/datePresets'

// URL state synchronization with proper browser navigation
const router = useRouter()
const route = useRoute()
const urlState = useNavigableUrlState({
  defaultView: 'grouped',
  defaultPageSize: 20, // Changed: 20 groups per page instead of 100 alerts
  defaultSortBy: 'detected_at',
  defaultSortOrder: 'desc',
  defaultGroupedSortBy: 'total_count',
  defaultUngroupedSortBy: 'detected_at'
})

// Track if we're changing views to show appropriate loading state
const isChangingView = ref(false)

// Alert details dialog state
const detailsDialogOpen = ref(false)
const selectedAlertId = ref<string | null>(null)

// Handle navigation to filtered view when clicking on a classification
function handleViewAlertDetails(details: { sourceIp: string; targetIp: string; classification: string }) {
  // Mark as changing view
  isChangingView.value = true
  
  // Use navigateToDetails which properly creates a history entry
  urlState.navigateToDetails(details)
}

function openDeleteDialog(state: DeleteState) {
  deleteState.value = state
  deleteError.value = null
  deleteDialogOpen.value = true
}

// Get column definitions from composable
const { compactGroupedColumns, groupedColumns, ungroupedColumns, sortFieldMap, filterFieldMap } = useAlertTableColumns()


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
const rowSelection = ref<Record<string, boolean>>({})
const relativeRefreshToken = ref(0)

interface DeleteResponse {
  success: boolean
  deleted: number
  rows: number
}

type DeleteState =
  | { mode: 'single'; alert: AlertListItem }
  | { mode: 'bulk'; alerts: AlertListItem[] }
  | { mode: 'grouped'; sourceIp: string; targetIp: string; totalCount: number }

const deleteDialogOpen = ref(false)
const deleteState = ref<DeleteState | null>(null)
const deletePending = ref(false)
const deleteError = ref<string | null>(null)

// Compute the fetch URL dynamically based on isGrouped
const fetchUrl = computed(() => isGrouped.value ? '/api/alerts/groups' : '/api/alerts')

const getActivePresetId = (): DatePresetId | undefined => {
  const preset = urlState.filters.value.date_preset as string | undefined
  return isValidPresetId(preset) ? preset : undefined
}

// Create a comprehensive key that includes ALL reactive state
const fetchKey = computed(() => {
  // Include all URL state that affects data fetching
  const presetId = getActivePresetId()
  const relativeToken = presetId && isRelativePreset(presetId) ? relativeRefreshToken.value : 0
  const stateHash = JSON.stringify({
    view: urlState.view.value,
    page: urlState.page.value,
    pageSize: urlState.pageSize.value,
    sortBy: urlState.sortBy.value,
    sortOrder: urlState.sortOrder.value,
    filters: urlState.filters.value,
    relativeToken,
    // Don't include hiddenColumns or autoRefresh as they don't affect data
  })
  return `alerts-${btoa(stateHash)}`
})

// Compute query parameters reactively
const fetchQuery = computed(() => {
  const activePreset = getActivePresetId()
  const relativeToken = activePreset && isRelativePreset(activePreset) ? relativeRefreshToken.value : 0

  const mappedSortField = sortFieldMap[urlState.sortBy.value as keyof typeof sortFieldMap] || urlState.sortBy.value || 'detect_time'

  // Map filter fields
  const urlFilters = Object.fromEntries(
    Object.entries(urlState.filters.value).map(([key, value]) => [
      filterFieldMap[key as keyof typeof filterFieldMap] || key,
      value
    ])
  ) as Record<string, string | number>

  // CRITICAL FIX: Remove date_preset from filters before processing
  // The preset must be converted to actual dates, never sent to the backend
  delete urlFilters.date_preset

  // Check if we have a preset ID (from URL state or was in filters)
  const presetId = activePreset
  if (isValidPresetId(presetId)) {
    const { from } = getPresetRange(presetId)
    urlFilters.start_date = from.toISOString()

    // For relative presets, server handles "now" automatically when end_date is missing
    // For fixed presets (today, this-week, etc), send explicit end_date
    if (!isRelativePreset(presetId)) {
      const { to } = getPresetRange(presetId)
      urlFilters.end_date = to.toISOString()
    } else {
      // Explicitly remove end_date for relative presets so server uses "now"
      delete urlFilters.end_date
    }
  }

  // Apply default date filter ONLY if no dates exist after preset conversion
  // This ensures we ALWAYS have date filters applied
  if (!urlFilters.start_date && !urlFilters.end_date) {
    // Apply last-24-hours as default (relative preset)
    const { from } = getPresetRange('last-24-hours')
    urlFilters.start_date = from.toISOString()
    // Don't set end_date - let server use "now"
  }

  return {
    page: urlState.page.value,
    size: urlState.pageSize.value,
    sort_by: mappedSortField,
    sort_order: urlState.sortOrder.value,
    ...urlFilters
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
const columns = computed(() => isGrouped.value ? compactGroupedColumns : ungroupedColumns)

// Extract data and pagination from response
const displayData = computed(() => {
  if (!data.value) return []

  if (isGrouped.value) {
    // We know it's GroupedAlertResponse based on the fetch URL
    const response = data.value as GroupedAlertResponse

    // NEW: Use compact grouped format - one group per row
    const compactGroups: CompactGroupedAlert[] = response.groups?.map((group, index) => ({
      ...group,
      groupIndex: index
    })) || []

    return compactGroups
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

// Track how many rows we render and how many alerts they represent
const tableTotals = computed(() => {
  if (!data.value) return { rows: 0, alerts: 0, total: 0 }

  if (isGrouped.value) {
    const response = data.value as GroupedAlertResponse
    const alerts = typeof response.total_alerts === 'number'
      ? response.total_alerts
      : (response.groups || []).reduce((total, group) => {
        if (typeof group.total_count === 'number') {
          return total + group.total_count
        }

        if (!group.alerts?.length) return total
        return total + group.alerts.reduce((groupTotal, alert) => groupTotal + alert.count, 0)
      }, 0)

    return {
      rows: displayData.value.length,
      alerts,
      total: response.pagination?.total || displayData.value.length
    }
  }

  // Ungrouped: show current page count and total from pagination
  const response = data.value as AlertListResponse
  const rows = displayData.value.length
  const total = response.pagination?.total || rows

  return { rows, alerts: rows, total }
})

// Define table data type - includes compact grouped alerts
type TableDataItem = CompactGroupedAlert | AlertListItem;

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
    if (isGrouped.value && 'total_count' in row && 'groupIndex' in row) {
      // Compact grouped alert
      return `group-${row.source_ipv4 || 'unknown'}-${row.target_ipv4 || 'unknown'}-${row.groupIndex}`
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
  const presetId = getActivePresetId()
  if (presetId && isRelativePreset(presetId)) {
    isSilentRefresh.value = true
    relativeRefreshToken.value = Date.now()
    return
  }
  
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
    isSilentRefresh.value = false
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
  table: table as Table<AlertListItem | FlattenedGroupedAlert | CompactGroupedAlert>,
  isGrouped,
  pending,
  relativeRefreshToken
})

// Handle view details event from AlertActions
function handleViewDetailsEvent(event: WindowEventMap['viewAlertDetails']) {
  selectedAlertId.value = event.detail.alertId
  detailsDialogOpen.value = true
}

function handleDeletionRequest(event: WindowEventMap['alertDeletionRequest']) {
  const detail = event.detail
  if (!detail) return

  if (detail.mode === 'single' && detail.alert) {
    openDeleteDialog({ mode: 'single', alert: detail.alert })
  } else if (detail.mode === 'grouped' && detail.sourceIp && detail.targetIp) {
    openDeleteDialog({
      mode: 'grouped',
      sourceIp: detail.sourceIp,
      targetIp: detail.targetIp,
      totalCount: detail.totalCount ?? 0,
    })
  }
}

const handleBulkDelete = () => {
  if (isGrouped.value) return
  const selectedRows = table.getSelectedRowModel().rows
  const alerts = selectedRows
    .map((row) => row.original)
    .filter((item): item is AlertListItem => item !== undefined && typeof item === 'object' && 'id' in item)

  if (!alerts.length) {
    return
  }

  openDeleteDialog({ mode: 'bulk', alerts })
}

const deleteActionLabel = computed(() => {
  if (!deleteState.value) return 'Delete'
  if (deleteState.value.mode === 'single') return 'Delete alert'
  if (deleteState.value.mode === 'bulk') return `Delete ${deleteState.value.alerts.length} alert${deleteState.value.alerts.length === 1 ? '' : 's'}`
  return 'Delete group'
})

async function confirmDeletion() {
  if (!deleteState.value) return

  deletePending.value = true
  deleteError.value = null

  try {
    if (deleteState.value.mode === 'grouped') {
      await $fetch<DeleteResponse>('/api/alerts', {
        method: 'DELETE',
        query: {
          source_ip: deleteState.value.sourceIp,
          target_ip: deleteState.value.targetIp,
        },
      })
    } else {
      const ids = deleteState.value.mode === 'single'
        ? [deleteState.value.alert.id]
        : deleteState.value.alerts.map((alert) => alert.id)

      await $fetch<DeleteResponse>('/api/alerts', {
        method: 'DELETE',
        query: {
          ids: ids.join(','),
        },
      })
    }

    deleteDialogOpen.value = false
    deleteState.value = null
    rowSelection.value = {}

    await refresh()
  } catch (error) {
    const fetchError = error as FetchError & { data?: { detail?: string } }
    deleteError.value = fetchError?.data?.detail || fetchError?.message || 'Failed to delete alerts.'
  } finally {
    deletePending.value = false
  }
}

if (process.client) {
  useEventListener(window, 'viewAlertDetails', handleViewDetailsEvent)
  useEventListener(window, 'alertDeletionRequest', handleDeletionRequest)
}

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
      @bulkDelete="handleBulkDelete"
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
      <div class="flex items-center gap-6">
        <!-- Count display -->
        <div class="flex items-baseline gap-2">
          <template v-if="isGrouped">
            <div class="flex items-baseline gap-1.5">
              <span class="text-sm font-semibold text-foreground">{{ tableTotals.rows }}</span>
              <span class="text-xs text-muted-foreground">groups</span>
            </div>
            <span class="text-muted-foreground/40">•</span>
            <div class="flex items-baseline gap-1.5">
              <span class="text-sm font-semibold text-foreground">{{ tableTotals.alerts }}</span>
              <span class="text-xs text-muted-foreground">total alerts</span>
            </div>
          </template>
          <template v-else>
            <div class="flex items-baseline gap-1.5">
              <span class="text-sm font-semibold text-foreground">{{ tableTotals.rows }}</span>
              <span class="text-xs text-muted-foreground">showing</span>
            </div>
            <span class="text-muted-foreground/40">•</span>
            <div class="flex items-baseline gap-1.5">
              <span class="text-sm font-semibold text-foreground">{{ tableTotals.total.toLocaleString() }}</span>
              <span class="text-xs text-muted-foreground">total</span>
            </div>
          </template>
        </div>

        <!-- Page size selector -->
        <div class="flex items-center gap-2">
          <span class="text-xs text-muted-foreground">Per page</span>
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
              <SelectItem value="200">200</SelectItem>
            </SelectContent>
          </Select>
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
    
    <!-- Alert Details Dialog -->
    <AlertDetailsDialog 
      v-model:open="detailsDialogOpen"
      :alert-id="selectedAlertId"
    />

    <AlertDialog v-model:open="deleteDialogOpen">
    <AlertDialogContent class="w-full max-w-[520px] space-y-6">
      <AlertDialogHeader class="space-y-3">
        <div class="flex items-center gap-2 text-destructive">
          <Icon name="lucide:shield-alert" class="h-5 w-5" aria-hidden="true" />
          <AlertDialogTitle class="text-base font-semibold">
            <span class="sr-only">Warning:</span>
            <template v-if="deleteState?.mode === 'grouped'">
              Delete grouped alerts
            </template>
            <template v-else-if="deleteState?.mode === 'bulk'">
              Delete selected alerts
            </template>
            <template v-else>
              Delete alert
            </template>
          </AlertDialogTitle>
        </div>
        <AlertDialogDescription class="text-sm leading-relaxed text-muted-foreground">
          <span class="font-semibold text-destructive">Warning:</span>
          This action cannot be undone and permanently removes alert data from the Prelude database.
        </AlertDialogDescription>
      </AlertDialogHeader>

      <div v-if="deleteState?.mode === 'single'" class="space-y-4 rounded-lg border border-border/70 bg-muted/40 p-4">
        <dl class="space-y-3 text-sm">
          <div class="space-y-1">
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground/80">Alert ID</dt>
            <dd class="font-mono text-sm">#{{ deleteState.alert.id }}</dd>
          </div>
          <div v-if="deleteState.alert.classification_text" class="space-y-1">
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground/80">Classification</dt>
            <dd class="rounded-md bg-muted px-2 py-1 text-xs font-medium leading-snug text-foreground/80 break-words">
              {{ deleteState.alert.classification_text }}
            </dd>
          </div>
          <div class="space-y-1">
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground/80">Source → Target</dt>
            <dd class="font-mono text-xs text-foreground">
              {{ deleteState.alert.source_ipv4 || '—' }} → {{ deleteState.alert.target_ipv4 || '—' }}
            </dd>
          </div>
        </dl>
      </div>

      <div v-else-if="deleteState?.mode === 'bulk'" class="space-y-3 rounded-lg border border-border/70 bg-muted/40 p-4 text-sm">
        <p class="font-medium">{{ deleteState.alerts.length }} alerts selected</p>
        <p class="text-muted-foreground">
          All selected alerts and their related records will be erased immediately.
        </p>
      </div>

      <div v-else-if="deleteState?.mode === 'grouped'" class="space-y-4 rounded-lg border border-border/70 bg-muted/40 p-4">
        <dl class="space-y-3 text-sm">
          <div class="space-y-1">
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground/80">Source IP</dt>
            <dd class="font-mono text-xs break-all">{{ deleteState.sourceIp }}</dd>
          </div>
          <div class="space-y-1">
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground/80">Target IP</dt>
            <dd class="font-mono text-xs break-all">{{ deleteState.targetIp }}</dd>
          </div>
          <p class="text-muted-foreground">
            {{ deleteState.totalCount }} alert{{ deleteState.totalCount === 1 ? '' : 's' }} referencing this IP pair will be removed across all related tables.
          </p>
        </dl>
      </div>

      <p v-if="deleteError" class="text-sm text-destructive">
        {{ deleteError }}
      </p>

      <AlertDialogFooter class="flex items-center justify-between gap-2">
        <AlertDialogCancel :disabled="deletePending" class="border-border">
          Cancel
        </AlertDialogCancel>
        <AlertDialogAction
          class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          :disabled="deletePending"
          @click="confirmDeletion"
        >
          <span v-if="deletePending" class="mr-2 inline-flex h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" />
          {{ deleteActionLabel }}
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
    </AlertDialog>
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
