<script setup lang="ts">
import type { Table } from '@tanstack/vue-table'
import type { Alert } from '~/composables/useAlerts'

interface Props {
  table: Table<Alert>
}

const props = defineProps<Props>()
const isOpen = ref(false)

const columns = computed(() => props.table.getAllColumns()
  .filter(
    column =>
      typeof column.accessorFn !== 'undefined' && column.getCanHide(),
  ))

const selectedColumns = ref<string[]>(
  columns.value
    .filter(column => column.getIsVisible())
    .map(column => column.id)
)

const handleColumnVisibilityChange = (value: string, e: Event) => {
  // Prevent the dropdown from closing when selecting items
  e.preventDefault()
  
  const newSelectedColumns = selectedColumns.value.includes(value)
    ? selectedColumns.value.filter(id => id !== value)
    : [...selectedColumns.value, value]
  
  selectedColumns.value = newSelectedColumns
  
  columns.value.forEach(column => {
    column.toggleVisibility(newSelectedColumns.includes(column.id))
  })
}
</script>

<template>
  <div class="flex items-center">
    <ClientOnly>
      <DropdownMenu v-model:open="isOpen">
        <DropdownMenuTrigger as-child>
          <Button
            variant="outline"
            size="sm"
            class="hidden h-8 ml-auto lg:flex"
          >
            <Icon name="lucide:list-filter" class="w-4 h-4 mr-2" />
            View Columns
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" class="w-[200px]">
          <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuCheckboxItem
            v-for="column in columns"
            :key="column.id"
            :checked="selectedColumns.includes(column.id)"
            @select="(e) => handleColumnVisibilityChange(column.id, e)"
            class="capitalize"
          >
            {{ column.id }}
          </DropdownMenuCheckboxItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <!-- Fallback for when JavaScript is disabled or during SSR -->
      <template #fallback>
        <Button
          variant="outline"
          size="sm"
          class="hidden h-8 ml-auto lg:flex"
          disabled
        >
          <Icon name="lucide:list-filter" class="w-4 h-4 mr-2" />
          View Columns
        </Button>
      </template>
    </ClientOnly>
  </div>
</template>