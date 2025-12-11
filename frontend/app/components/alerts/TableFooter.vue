<template>
  <footer
    class="flex w-full flex-col items-center justify-between gap-4 border-t border-border bg-muted/40 px-6 py-4 text-sm sm:flex-row sm:h-14 sm:py-0"
    role="contentinfo" aria-label="Pagination and summary">
    <!-- Section 1 (Left): Contextual Information + Page Size -->
    <div class="flex flex-col items-center gap-4 sm:flex-row sm:gap-6">

      <!-- Summary Text -->
      <div class="text-muted-foreground text-center sm:text-left min-w-0 text-sm">
        <span class="truncate block">{{ summaryText }}</span>
      </div>

      <!-- Page Size Selector -->
      <Select :model-value="String(pageSize)" @update:model-value="handleUpdatePageSize" :disabled="pending">
        <SelectTrigger class="h-8 w-[90px] bg-background" aria-label="Rows per page">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel class="text-xs text-muted-foreground font-normal pl-2 py-1">
              Rows per page
            </SelectLabel>
            <SelectItem v-for="option in pageSizeOptions" :key="option" :value="String(option)">
              {{ option }}
            </SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>

    </div>

    <!-- Section 2 (Right): Pagination Controls -->
    <div class="flex items-center gap-2">

      <!-- Previous Button -->
      <Button variant="outline" class="h-8 px-3 bg-background" :disabled="isFirstPage || pending"
        @click="updatePage(currentPage - 1)" aria-label="Go to previous page">
        <Icon name="lucide:chevron-left" class="h-4 w-4 mr-1" />
        <span>Prev</span>
      </Button>

      <!-- Page Indicator -->
      <div class="text-muted-foreground min-w-[80px] text-center tabular-nums font-medium text-sm">
        Page {{ currentPage }} of {{ totalPages }}
      </div>

      <!-- Next Button -->
      <Button variant="outline" class="h-8 px-3 bg-background" :disabled="isLastPage || pending"
        @click="updatePage(currentPage + 1)" aria-label="Go to next page">
        <span>Next</span>
        <Icon name="lucide:chevron-right" class="h-4 w-4 ml-1" />
      </Button>
    </div>

  </footer>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface TableTotals {
  rows: number
  alerts: number
  total: number
}

const props = withDefaults(defineProps<{
  isGrouped: boolean
  totals: TableTotals
  pagination: PaginatedResponse
  currentPage: number
  pageSize: number
  pending: boolean
  pageSizeOptions?: number[]
}>(), {
  pageSizeOptions: () => [10, 20, 50, 100]
})

const emit = defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [size: number]
}>()

// --- Computed Logic ---

const totalItems = computed(() => props.pagination.total || props.totals.total || 0)

const totalPages = computed(() => {
  if (props.pagination.pages && props.pagination.pages > 0) return props.pagination.pages
  if (props.pageSize > 0 && totalItems.value) return Math.ceil(totalItems.value / props.pageSize)
  return 1
})

const isFirstPage = computed(() => props.currentPage <= 1)
const isLastPage = computed(() => props.currentPage >= totalPages.value)

const rangeStart = computed(() => {
  if (totalItems.value === 0) return 0
  return (props.currentPage - 1) * props.pageSize + 1
})

const rangeEnd = computed(() => {
  return Math.min(totalItems.value, props.currentPage * props.pageSize)
})

// Consolidated summary text logic
const summaryText = computed(() => {
  if (totalItems.value === 0) {
    return 'No results'
  }

  const start = rangeStart.value
  const end = rangeEnd.value
  const total = totalItems.value.toLocaleString()

  if (props.isGrouped) {
    const alertCount = props.totals.alerts.toLocaleString()
    return `${start}–${end} of ${total} groups (${alertCount} alerts)`
  }

  return `Showing ${start}–${end} of ${total} alerts`
})

// --- Actions ---

function updatePage(nextPage: number) {
  if (props.pending) return
  const safePage = Math.min(Math.max(nextPage, 1), totalPages.value)
  if (safePage !== props.currentPage) {
    emit('update:page', safePage)
  }
}

function handleUpdatePageSize(value: string | number | bigint | Record<string, any> | null) {
  if (props.pending || !value) return
  const size = Number(value)
  if (!Number.isNaN(size) && size > 0) {
    emit('update:pageSize', size)
    if (props.currentPage !== 1) emit('update:page', 1)
  }
}
</script>