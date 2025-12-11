<script setup lang="ts">
import type { Column } from '@tanstack/vue-table'
import { Icon } from '#components'
import { Button } from '@/components/ui/button'
import { computed } from 'vue'

interface Props {
  column: Column<any, any>
  title: string
}

const props = defineProps<Props>()

const isSorted = computed(() => props.column.getIsSorted())

const icon = computed(() => {
  if (isSorted.value === 'asc') return 'lucide:arrow-up'
  if (isSorted.value === 'desc') return 'lucide:arrow-down'
  return 'lucide:arrow-up-down'
})
</script>

<template>
  <!-- Sortable header -->
  <Button
    v-if="column.getCanSort()"
    variant="ghost"
    size="sm"
    class="-mx-3 h-8 justify-start uppercase"
    @click="column.toggleSorting(isSorted === 'asc')"
  >
    {{ title }}
    <Icon :name="icon" class="ml-2 size-4" />
  </Button>

  <!-- Non-sortable header -->
  <div v-else class="flex items-center h-8 text-sm font-medium uppercase">
    {{ title }}
  </div>
</template>
