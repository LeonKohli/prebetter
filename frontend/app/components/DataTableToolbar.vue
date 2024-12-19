<script setup lang="ts">
import type { Table } from '@tanstack/vue-table'
import type { Alert } from '~/composables/useAlerts'
import DataTableViewOptions from '@/components/DataTableViewOptions.vue'
import DataTableFacetedFilter from '@/components/DataTableFacetedFilter.vue'

interface Props {
  table: Table<Alert>
}

const props = defineProps<Props>()
const isFiltered = computed(() => props.table.getState().columnFilters.length > 0)
</script>

<template>
  <div class="flex items-center justify-between">
    <div class="flex items-center flex-1 space-x-2">
      <Input
        placeholder="Search alerts..."
        :model-value="(table.getColumn('classification_text')?.getFilterValue() as string) ?? ''"
        @input="table.getColumn('classification_text')?.setFilterValue($event.target.value)"
        class="h-8 w-[150px] lg:w-[250px]"
      />
      <DataTableFacetedFilter
        v-if="table.getColumn('severity')"
        :column="table.getColumn('severity')"
        title="Severity"
        :options="severityOptions"
      />
      <Button
        v-if="isFiltered"
        variant="ghost"
        class="h-8 px-2 lg:px-3"
        @click="table.resetColumnFilters()"
      >
        Reset
        <Icon name="lucide:x" class="w-4 h-4 ml-2" />
      </Button>
    </div>
    <DataTableViewOptions :table="table" />
  </div>
</template> 