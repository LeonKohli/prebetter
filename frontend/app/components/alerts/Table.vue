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
// URL state synchronization
const router = useRouter()
const route = useRoute()
const urlState = useNavigableUrlState({
  defaultView: 'grouped',
  defaultPageSize: 100,
  defaultSortBy: 'detected_at',
  defaultSortOrder: 'desc',
  defaultGroupedSortBy: 'detected_at',
  defaultUngroupedSortBy: 'detected_at'
})

// Data fetching (extracted to composable)
const {
  data,
  pending,
  error,
  status,
  refresh,
  execute,
  isGrouped,
  displayData,
  paginationInfo,
  tableTotals,
  fetchKey,
  relativeRefreshToken,
  getActivePresetId,
  triggerRelativeRefresh,
} = await useAlertsData(urlState)

// Local UI state
const isChangingView = ref(false)
const rowSelection = ref<Record<string, boolean>>({})

// Live mode / SSE (extracted to composable)
const {
  isLive,
  sseStatus,
  sseError,
  showLoadingOverlay,
  toggleLive,
  resetSilentRefresh,
} = useAlertsLiveMode({
  status,
  rowSelection,
  refresh,
  getActivePresetId,
  triggerRelativeRefresh,
})

// Dialog state
const detailsDialogOpen = ref(false)
const selectedAlertId = ref<string | null>(null)

type DeleteState =
  | { mode: 'single'; alert: AlertListItem }
  | { mode: 'bulk'; alerts: AlertListItem[] }
  | { mode: 'grouped'; sourceIp: string; targetIp: string; totalCount: number }

const deleteDialogOpen = ref(false)
const deleteState = ref<DeleteState | null>(null)

// Column definitions (TimeAgo component handles reactivity internally)
const { compactGroupedColumns, ungroupedColumns } = useAlertTableColumns()
const columns = computed(() => isGrouped.value ? compactGroupedColumns : ungroupedColumns)

// Table state sync with URL
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

// Table data type
type TableDataItem = CompactGroupedAlert | AlertListItem

// Table instance
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
      return `group-${row.source_ipv4 || 'unknown'}-${row.target_ipv4 || 'unknown'}-${row.groupIndex}`
    } else if ('id' in row) {
      return row.id
    }
    return 'unknown'
  },
  // TanStack Table meta: type-safe callbacks passed to column definitions
  meta: {
    onViewDetails: (alertId: string) => {
      selectedAlertId.value = alertId
      detailsDialogOpen.value = true
    },
    onRequestDeleteSingle: (alert: AlertListItem) => {
      openDeleteDialog({ mode: 'single', alert })
    },
    onRequestDeleteGroup: (group: CompactGroupedAlert | FlattenedGroupedAlert) => {
      openDeleteDialog({
        mode: 'grouped',
        sourceIp: group.source_ipv4 || '',
        targetIp: group.target_ipv4 || '',
        totalCount: group.total_count ?? 0,
      })
    },
  },
})

// Debounced fetch execution
watchDebounced(fetchKey, () => execute(), { debounce: 50 })

// Reset flags on status change
watch(status, (newStatus) => {
  if (newStatus === 'success' || newStatus === 'error') {
    isChangingView.value = false
    resetSilentRefresh()
  }
})

// Provide context for child components
provideAlertTableContext({
  urlState,
  table: table as Table<AlertListItem | FlattenedGroupedAlert | CompactGroupedAlert>,
  isGrouped,
  pending,
  relativeRefreshToken
})

// Event handlers
function handleToggleView() {
  const newView = urlState.view.value === 'grouped' ? 'ungrouped' : 'grouped'
  isChangingView.value = true
  rowSelection.value = {}

  const newQuery: Record<string, string | undefined> = { ...route.query as Record<string, string | undefined>, view: newView }
  delete newQuery.sort

  if (urlState.page.value !== 1) newQuery.page = '1'

  if (newView === 'grouped' && urlState.filters.value.classification_text) {
    const currentFilters = { ...urlState.filters.value }
    delete currentFilters.classification_text
    newQuery.filter = Object.keys(currentFilters).length > 0 ? JSON.stringify(currentFilters) : undefined
  }

  router.push({ query: newQuery })
}

function openDeleteDialog(state: DeleteState) {
  deleteState.value = state
  deleteDialogOpen.value = true
}

function handleDeleteComplete() {
  deleteState.value = null
  rowSelection.value = {}
  refresh()
}

function handleBulkDelete() {
  if (isGrouped.value) return
  const alerts = table.getSelectedRowModel().rows
    .map((row) => row.original)
    .filter((item): item is AlertListItem => item !== undefined && 'id' in item)

  if (alerts.length) openDeleteDialog({ mode: 'bulk', alerts })
}

</script>

<template>
  <div class="w-full flex-1 min-h-0 flex flex-col gap-2">
    <AlertsToolbar
      :is-live="isLive"
      :sse-status="sseStatus"
      :sse-error="sseError"
      @toggle-view="handleToggleView"
      @toggle-live="toggleLive"
      @bulk-delete="handleBulkDelete"
      @refresh="refresh"
    />

    <div class="flex-1 min-h-0 rounded-lg border overflow-hidden flex flex-col">
      <div class="flex-1 overflow-auto relative overscroll-none">
        <TableFlat role="table" aria-label="Security alerts table">
          <TableHeader class="sticky top-0 z-10">
            <TableRow v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id" class="h-10">
              <TableHead
                v-for="(header, idx) in headerGroup.headers"
                :key="header.id"
                :class="['bg-muted py-2 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider', idx > 0 && 'border-r']"
              >
                <FlexRender v-if="!header.isPlaceholder" :render="header.column.columnDef.header" :props="header.getContext()" />
              </TableHead>
            </TableRow>
          </TableHeader>

          <TableBody class="relative">
            <Transition name="fade">
              <div
                v-if="showLoadingOverlay && data"
                class="absolute inset-0 bg-background/40 z-10 pointer-events-none"
                role="status"
                aria-busy="true"
              />
            </Transition>

            <template v-if="status === 'idle' || (status === 'pending' && !data) || isChangingView">
              <TableRow v-for="i in 20" :key="`skeleton-${i}`" class="h-11 border-b border-border/40">
                <TableCell
                  v-for="(_, idx) in columns.length"
                  :key="`skeleton-${i}-${idx}`"
                  :class="['py-2 px-4', idx > 0 && 'border-r']"
                >
                  <div class="h-4 bg-muted animate-pulse rounded" />
                </TableCell>
              </TableRow>
            </template>

            <template v-else-if="table.getRowModel().rows?.length">
              <TableRow
                v-for="(row, rowIdx) in table.getRowModel().rows"
                :key="row.id"
                :data-state="row.getIsSelected() && 'selected'"
                :class="['h-11 border-b border-border/40 hover:bg-muted/50 transition-colors', rowIdx % 2 === 1 && 'bg-muted/30']"
              >
                <TableCell
                  v-for="(cell, cellIdx) in row.getVisibleCells()"
                  :key="cell.id"
                  :class="['py-2 px-4 text-sm', cellIdx > 0 && 'border-r']"
                >
                  <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
                </TableCell>
              </TableRow>
            </template>

            <TableRow v-else-if="!isChangingView && status !== 'pending'">
              <TableCell :colspan="columns.length" class="h-24 text-center">
                <span v-if="error">Error loading alerts. Please try again.</span>
                <span v-else>No alerts found.</span>
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
        @update:page="(page) => urlState.page.value = page"
        @update:page-size="(size) => urlState.pageSize.value = size"
      />
    </div>

    <AlertsDetailsDialog v-model:open="detailsDialogOpen" :alert-id="selectedAlertId" />
    <AlertsDeleteDialog v-model:open="deleteDialogOpen" :state="deleteState" @deleted="handleDeleteComplete" />
    <AlertsSelectionBar v-if="!isGrouped" @bulk-delete="handleBulkDelete" />
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
