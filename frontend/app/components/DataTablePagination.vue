<script setup lang="ts">
interface Props {
  currentPage: number
  pageSize: number
  totalItems: number
  totalPages: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [size: number]
}>()

const pageSizes = [10, 20, 50, 100]

const handlePageChange = (newPage: number) => {
  if (newPage >= 1 && newPage <= props.totalPages) {
    emit('update:page', newPage)
  }
}

const handlePageSizeChange = (newSize: string) => {
  emit('update:pageSize', parseInt(newSize))
}
</script>

<template>
  <div class="flex items-center justify-between px-2">
    <div class="flex-1 text-sm text-muted-foreground">
      Total {{ totalItems }} items
    </div>
    <div class="flex items-center space-x-6 lg:space-x-8">
      <div class="flex items-center space-x-2">
        <p class="text-sm font-medium">
          Rows per page
        </p>
        <Select
          :model-value="`${pageSize}`"
          @update:model-value="handlePageSizeChange"
        >
          <SelectTrigger class="h-8 w-[70px]">
            <SelectValue :placeholder="`${pageSize}`" />
          </SelectTrigger>
          <SelectContent side="top">
            <SelectItem
              v-for="size in pageSizes"
              :key="size"
              :value="`${size}`"
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
          :disabled="currentPage === 1"
          @click="handlePageChange(1)"
        >
          <span class="sr-only">Go to first page</span>
          <Icon name="lucide:chevrons-left" class="w-4 h-4" />
        </Button>
        <Button
          variant="outline"
          class="w-8 h-8 p-0"
          :disabled="currentPage === 1"
          @click="handlePageChange(currentPage - 1)"
        >
          <span class="sr-only">Go to previous page</span>
          <Icon name="lucide:chevron-left" class="w-4 h-4" />
        </Button>
        <Button
          variant="outline"
          class="w-8 h-8 p-0"
          :disabled="currentPage === totalPages"
          @click="handlePageChange(currentPage + 1)"
        >
          <span class="sr-only">Go to next page</span>
          <Icon name="lucide:chevron-right" class="w-4 h-4" />
        </Button>
        <Button
          variant="outline"
          class="hidden w-8 h-8 p-0 lg:flex"
          :disabled="currentPage === totalPages"
          @click="handlePageChange(totalPages)"
        >
          <span class="sr-only">Go to last page</span>
          <Icon name="lucide:chevrons-right" class="w-4 h-4" />
        </Button>
      </div>
    </div>
  </div>
</template> 