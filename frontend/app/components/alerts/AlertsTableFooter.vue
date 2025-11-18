<template>
  <footer
    class="border-t border-border bg-muted/20 px-4 py-3"
    role="contentinfo"
    aria-label="Alert table summary and pagination"
  >
    <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <!-- Totals / density info -->
      <div class="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm" aria-live="polite">
        <template v-if="isGrouped">
          <div class="flex items-baseline gap-1.5 text-foreground">
            <span class="text-base font-semibold">{{ totals.rows }}</span>
            <span class="text-xs text-muted-foreground">groups shown</span>
          </div>
          <span class="text-muted-foreground/50">•</span>
          <div class="flex items-baseline gap-1.5 text-foreground">
            <span class="text-base font-semibold">{{ totals.alerts.toLocaleString() }}</span>
            <span class="text-xs text-muted-foreground">total alerts</span>
          </div>
        </template>
        <template v-else>
          <div class="flex items-baseline gap-1.5 text-foreground">
            <span class="text-base font-semibold">{{ rangeLabel }}</span>
            <span class="text-xs text-muted-foreground">showing</span>
          </div>
          <span class="text-muted-foreground/50">•</span>
          <div class="flex items-baseline gap-1.5 text-foreground">
            <span class="text-base font-semibold">{{ totals.total.toLocaleString() }}</span>
            <span class="text-xs text-muted-foreground">total</span>
          </div>
        </template>
      </div>

      <!-- Controls -->
      <div class="flex w-full flex-wrap items-center gap-3 md:w-auto md:justify-end">
        <div class="flex items-center gap-2 text-sm text-muted-foreground">
          <span>Per page</span>
          <Select
            :model-value="String(pageSize)"
            @update:model-value="handleUpdatePageSize"
            aria-label="Select page size"
          >
            <SelectTrigger class="h-8 w-[90px] border-border" :disabled="pending">
              <SelectValue :placeholder="pageSize" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="option in pageSizeOptions" :key="option" :value="String(option)">
                {{ option }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="flex items-center gap-2" role="navigation" aria-label="Table pagination controls">
          <Button
            variant="outline"
            size="sm"
            class="h-8 px-3 text-xs font-medium border-border"
            :disabled="isFirstPage || pending"
            @click="() => updatePage(currentPage - 1)"
          >
            <Icon name="lucide:chevron-left" class="mr-1 h-3.5 w-3.5" />
            Previous
          </Button>

          <div class="flex items-center gap-1 text-sm font-medium text-muted-foreground">
            <span>Page</span>
            <span class="text-foreground">{{ currentPage }}</span>
            <span>of {{ totalPages }}</span>
          </div>

          <Button
            variant="outline"
            size="sm"
            class="h-8 px-3 text-xs font-medium border-border"
            :disabled="isLastPage || pending"
            @click="() => updatePage(currentPage + 1)"
          >
            Next
            <Icon name="lucide:chevron-right" class="ml-1 h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import type { PaginatedResponse } from '@/shared/types/alerts'

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

const totalItems = computed(() => props.pagination.total || props.totals.total || 0)
const totalPages = computed(() => {
  if (props.pagination.pages && props.pagination.pages > 0) {
    return props.pagination.pages
  }
  if (props.pageSize > 0 && totalItems.value) {
    return Math.max(1, Math.ceil(totalItems.value / props.pageSize))
  }
  return 1
})
const isFirstPage = computed(() => props.currentPage <= 1)
const isLastPage = computed(() => props.currentPage >= totalPages.value)

const rangeStart = computed(() => {
  if (!totalItems.value) return 0
  return (props.currentPage - 1) * props.pageSize + 1
})

const rangeEnd = computed(() => {
  if (!totalItems.value) return 0
  return Math.min(totalItems.value, props.currentPage * props.pageSize)
})

const rangeLabel = computed(() => {
  if (!rangeStart.value || !rangeEnd.value) return String(props.totals.rows)
  return `${rangeStart.value}–${rangeEnd.value}`
})

function updatePage(nextPage: number) {
  const safePage = Math.min(Math.max(nextPage, 1), totalPages.value)
  if (safePage !== props.currentPage) {
    emit('update:page', safePage)
  }
}

function handleUpdatePageSize(value: string) {
  const size = Number(value)
  if (!Number.isNaN(size) && size > 0) {
    emit('update:pageSize', size)
  }
}
</script>
