<script setup lang="ts">
import type { Column } from '@tanstack/vue-table'
import type { Alert } from '~/composables/useAlerts'
import { Button } from '@/components/ui/button'

interface Props {
  column: Column<Alert, unknown>
  title: string
}

const props = defineProps<Props>()

const toggleSorting = () => {
  const currentSort = props.column.getIsSorted()
  if (!currentSort) {
    props.column.toggleSorting(false) // Set to ascending
  } else if (currentSort === 'asc') {
    props.column.toggleSorting(true) // Set to descending
  } else {
    props.column.clearSorting() // Clear sorting
  }
}
</script>

<script lang="ts">
export default {
  inheritAttrs: false,
}
</script>

<template>
  <div v-if="column.getCanSort()" :class="['flex items-center space-x-2', $attrs.class ?? '']">
    <Button 
      variant="ghost"
      size="sm"
      class="h-8 -ml-3"
      @click="toggleSorting"
    >
      <span>{{ title }}</span>
      <Icon
        v-if="column.getIsSorted() === 'desc'"
        name="lucide:arrow-down"
        class="w-4 h-4 ml-2"
      />
      <Icon
        v-else-if="column.getIsSorted() === 'asc'"
        name="lucide:arrow-up"
        class="w-4 h-4 ml-2"
      />
      <Icon
        v-else
        name="lucide:chevrons-up-down"
        class="w-4 h-4 ml-2"
      />
    </Button>
  </div>
  <div v-else :class="$attrs.class">
    {{ title }}
  </div>
</template> 