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
import { useIntervalFn, useDocumentVisibility, useEventListener, watchDebounced } from '@vueuse/core'
import type { FetchError } from 'ofetch'
import AlertDetailsDialog from '@/components/alerts/AlertDetailsDialog.vue'
import AlertsSelectionBar from '@/components/alerts/AlertsSelectionBar.vue'
import { valueUpdater } from '@/utils/utils'
import { getPresetRange, isRelativePreset, isValidPresetId, type DatePresetId } from '@/utils/datePresets'

// URL state synchronization with proper browser navigation
const router = useRouter()
const route = useRoute()
const urlState = useNavigableUrlState({
  defaultView: 'grouped',
  defaultPageSize: 100, // Universal default: 100 items per page
  defaultSortBy: 'detected_at',
  defaultSortOrder: 'desc',
  defaultGroupedSortBy: 'detected_at',
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
  <div class="w-full h-full flex flex-col">
    <!-- Toolbar -->
    <AlertsToolbar
      @toggleView="handleToggleView"
      @startAutoRefresh="startAutoRefresh"
      @stopAutoRefresh="stopAutoRefresh"
      @bulkDelete="handleBulkDelete"
    />

    <!-- Table + Pagination unified card -->
    <div
      class="flex-1 min-h-0 mt-2 rounded-lg border overflow-hidden flex flex-col"
    >
      <!-- Table area (scrollable) -->
      <div class="flex-1 overflow-auto relative overscroll-none">
        <TableFlat role="table" aria-label="Security alerts table">
          <TableHeader class="sticky top-0 z-10">
            <TableRow v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id" class="h-10">
              <TableHead
                v-for="(header, index) in headerGroup.headers"
                :key="header.id"
                :class="[
                  'bg-muted py-2 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider',
                  index === 0 ? '' : 'border-r',
                  index === headerGroup.headers.length - 1 ? '' : ''
                ]"
              >
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
              <TableRow v-for="i in 20" :key="`skeleton-${i}`" class="h-11 border-b border-border/40 hover:bg-muted/50">
                <TableCell
                  v-for="(j, index) in columns.length"
                  :key="`skeleton-${i}-${j}`"
                  :class="['py-2 px-4', index === 0 ? '' : 'border-r', index === columns.length - 1 ? '' : '']"
                >
                  <div class="h-4 bg-muted animate-pulse rounded" />
                </TableCell>
              </TableRow>
            </template>
            <!-- Show data when available -->
            <template v-else-if="table.getRowModel().rows?.length">
              <template v-for="(row, index) in table.getRowModel().rows" :key="row.id">
                <TableRow :data-state="row.getIsSelected() && 'selected'" :class="['h-11 border-b border-border/40 hover:bg-muted/50 transition-colors', index % 2 === 1 && 'bg-muted/30']">
                  <TableCell
                    v-for="(cell, index) in row.getVisibleCells()"
                    :key="cell.id"
                    :class="[
                      'py-2 px-4 text-sm font-normal',
                      index === 0 ? '' : 'border-r',
                      index === row.getVisibleCells().length - 1 ? '' : ''
                    ]"
                  >
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
        </TableFlat>
      </div>

      <AlertsTableFooter
        class="shrink-0"
        :is-grouped="isGrouped"
        :totals="tableTotals"
        :pagination="paginationInfo"
        :current-page="urlState.page.value"
        :page-size="urlState.pageSize.value"
        :pending="pending"
        @update:page="(page) => { urlState.page.value = page }"
        @update:page-size="(size) => { urlState.pageSize.value = size }"
      />
    </div>

    <!-- Alert Details Dialog -->
    <AlertDetailsDialog 
      v-model:open="detailsDialogOpen"
      :alert-id="selectedAlertId"
    />

    <AlertDialog v-model:open="deleteDialogOpen">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle class="flex items-center gap-2">
            <Icon name="lucide:trash-2" class="h-5 w-5 text-destructive" />
            <template v-if="deleteState?.mode === 'grouped'">
              Delete Grouped Alerts
            </template>
            <template v-else-if="deleteState?.mode === 'bulk'">
              Delete Selected Alerts
            </template>
            <template v-else>
              Delete Alert
            </template>
          </AlertDialogTitle>
          <AlertDialogDescription>
            This action cannot be undone. This will permanently delete the alert data from the Prelude database.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <!-- Single Alert Details -->
        <div v-if="deleteState?.mode === 'single'" class="rounded-lg border bg-muted/50 p-4">
          <dl class="space-y-3 text-sm">
            <div class="flex items-start justify-between gap-4">
              <dt class="text-xs font-medium text-muted-foreground">Alert ID</dt>
              <dd class="font-mono text-sm">#{{ deleteState.alert.id }}</dd>
            </div>
            <div v-if="deleteState.alert.classification_text" class="flex items-start justify-between gap-4">
              <dt class="text-xs font-medium text-muted-foreground">Classification</dt>
              <dd class="text-right text-sm break-words max-w-[60%]">
                {{ deleteState.alert.classification_text }}
              </dd>
            </div>
            <div class="flex items-start justify-between gap-4">
              <dt class="text-xs font-medium text-muted-foreground">Source</dt>
              <dd class="font-mono text-xs">{{ deleteState.alert.source_ipv4 || '—' }}</dd>
            </div>
            <div class="flex items-start justify-between gap-4">
              <dt class="text-xs font-medium text-muted-foreground">Target</dt>
              <dd class="font-mono text-xs">{{ deleteState.alert.target_ipv4 || '—' }}</dd>
            </div>
          </dl>
        </div>

        <!-- Bulk Selection Info -->
        <div v-else-if="deleteState?.mode === 'bulk'" class="rounded-lg border bg-muted/50 p-4">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive/10">
              <Icon name="lucide:layers" class="h-5 w-5 text-destructive" />
            </div>
            <div class="flex-1 space-y-1">
              <p class="text-sm font-medium">
                {{ deleteState.alerts.length }} alert{{ deleteState.alerts.length === 1 ? '' : 's' }} selected
              </p>
              <p class="text-xs text-muted-foreground">
                All related records will be permanently removed
              </p>
            </div>
          </div>
        </div>

        <!-- Grouped Alerts Info -->
        <div v-else-if="deleteState?.mode === 'grouped'" class="rounded-lg border bg-muted/50 p-4">
          <div class="space-y-4">
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive/10">
                <Icon name="lucide:network" class="h-5 w-5 text-destructive" />
              </div>
              <div class="flex-1 space-y-1">
                <p class="text-sm font-medium">IP Pair Group</p>
                <p class="text-xs text-muted-foreground">
                  {{ deleteState.totalCount }} alert{{ deleteState.totalCount === 1 ? '' : 's' }} affected
                </p>
              </div>
            </div>
            <dl class="space-y-2 text-sm border-t pt-3">
              <div class="flex items-center justify-between gap-4">
                <dt class="text-xs font-medium text-muted-foreground">Source IP</dt>
                <dd class="font-mono text-xs">{{ deleteState.sourceIp }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4">
                <dt class="text-xs font-medium text-muted-foreground">Target IP</dt>
                <dd class="font-mono text-xs">{{ deleteState.targetIp }}</dd>
              </div>
            </dl>
          </div>
        </div>

        <!-- Error Display -->
        <div v-if="deleteError" class="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-3">
          <Icon name="lucide:alert-circle" class="h-4 w-4 shrink-0 text-destructive" />
          <p class="text-sm text-destructive">{{ deleteError }}</p>
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel as-child>
            <Button variant="outline" :disabled="deletePending">
              Cancel
            </Button>
          </AlertDialogCancel>
          <AlertDialogAction as-child>
            <Button variant="destructive" :disabled="deletePending" @click="confirmDeletion">
              <Icon v-if="deletePending" name="lucide:loader-2" class="mr-2 h-4 w-4 animate-spin" />
              {{ deleteActionLabel }}
            </Button>
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <!-- Floating Selection Bar -->
    <AlertsSelectionBar
      v-if="!isGrouped"
      @bulkDelete="handleBulkDelete"
    />
  </div>
</template>

<style scoped>
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
