<script setup lang="ts">
interface Props {
  currentPage: number
  pageSize: number
  totalItems: number
  totalPages: number
  selectedRows?: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [size: number]
}>()

const pageSizes = [10, 20, 50, 100]

// Computed properties to ensure consistent string representations
const currentPageSize = computed(() => String(props.pageSize))
const hasSelectedRows = computed(() => typeof props.selectedRows === 'number')

const handlePageChange = (newPage: number) => {
  if (newPage >= 1 && newPage <= props.totalPages) {
    emit('update:page', newPage)
  }
}

const handlePageSizeChange = (newSize: string) => {
  const parsed = parseInt(newSize, 10)
  if (!isNaN(parsed)) {
    emit('update:pageSize', parsed)
  }
}
</script>

<template>
  <div class="flex items-center justify-between px-2">
    <div class="flex-1 min-w-[200px] text-sm text-muted-foreground">
      <div class="min-h-[20px]">
        <template v-if="hasSelectedRows">
          {{ selectedRows }} of {{ totalItems }} row(s) selected.
        </template>
        <template v-else>
          {{ totalItems }} items total
        </template>
      </div>
    </div>
    <div class="flex items-center space-x-6 lg:space-x-8">
      <div class="flex items-center space-x-2">
        <p class="text-sm font-medium">
          Rows per page
        </p>
        <Select
          :model-value="currentPageSize"
          @update:model-value="handlePageSizeChange"
        >
          <SelectTrigger class="h-8 w-[70px]">
            <SelectValue :placeholder="currentPageSize" />
          </SelectTrigger>
          <SelectContent side="top">
            <SelectItem
              v-for="size in pageSizes"
              :key="size"
              :value="String(size)"
            >
              {{ size }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div class="flex w-[100px] items-center justify-center text-sm font-medium">
        Page {{ currentPage }} of {{ totalPages }}
      </div>
      <div class="flex items-center space-x-2">
        <Button
          variant="outline"
          class="hidden w-8 h-8 p-0 lg:flex"
          @click="handlePageChange(1)"
        >
          <ClientOnly>
            <template #fallback>
              <span class="sr-only">Go to first page</span>
              <Icon name="lucide:chevrons-left" class="w-4 h-4" />
            </template>
            <div class="flex items-center justify-center w-full h-full" :class="{ 'pointer-events-none opacity-50': currentPage <= 1 }">
              <span class="sr-only">Go to first page</span>
              <Icon name="lucide:chevrons-left" class="w-4 h-4" />
            </div>
          </ClientOnly>
        </Button>
        <Button
          variant="outline"
          class="w-8 h-8 p-0"
          @click="handlePageChange(currentPage - 1)"
        >
          <ClientOnly>
            <template #fallback>
              <span class="sr-only">Go to previous page</span>
              <Icon name="lucide:chevron-left" class="w-4 h-4" />
            </template>
            <div class="flex items-center justify-center w-full h-full" :class="{ 'pointer-events-none opacity-50': currentPage <= 1 }">
              <span class="sr-only">Go to previous page</span>
              <Icon name="lucide:chevron-left" class="w-4 h-4" />
            </div>
          </ClientOnly>
        </Button>
        <Button
          variant="outline"
          class="w-8 h-8 p-0"
          @click="handlePageChange(currentPage + 1)"
        >
          <ClientOnly>
            <template #fallback>
              <span class="sr-only">Go to next page</span>
              <Icon name="lucide:chevron-right" class="w-4 h-4" />
            </template>
            <div class="flex items-center justify-center w-full h-full" :class="{ 'pointer-events-none opacity-50': currentPage >= totalPages }">
              <span class="sr-only">Go to next page</span>
              <Icon name="lucide:chevron-right" class="w-4 h-4" />
            </div>
          </ClientOnly>
        </Button>
        <Button
          variant="outline"
          class="hidden w-8 h-8 p-0 lg:flex"
          @click="handlePageChange(totalPages)"
        >
          <ClientOnly>
            <template #fallback>
              <span class="sr-only">Go to last page</span>
              <Icon name="lucide:chevrons-right" class="w-4 h-4" />
            </template>
            <div class="flex items-center justify-center w-full h-full" :class="{ 'pointer-events-none opacity-50': currentPage >= totalPages }">
              <span class="sr-only">Go to last page</span>
              <Icon name="lucide:chevrons-right" class="w-4 h-4" />
            </div>
          </ClientOnly>
        </Button>
      </div>
    </div>
  </div>
</template>