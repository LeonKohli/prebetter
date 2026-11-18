<script setup lang="ts">
import type { RequestFilterField } from '~~/shared/types/alerts'
import { requestFilterValues, toggleRequestValue, type RequestFilterMode } from '@/utils/requestFilters'

/** Two buttons next to a value of the alert: show only alerts with it, or hide them. */
const props = defineProps<{
  field: RequestFilterField
  value: string
}>()

const emit = defineEmits<{
  filtered: []
}>()

const { urlState } = useAlertTableContext()

function apply(mode: RequestFilterMode) {
  const filters = urlState.filters.value
  // Choosing what is already chosen changes nothing; the other choice for the value is dropped.
  if (!requestFilterValues(filters, props.field, mode).includes(props.value)) {
    urlState.filters.value = toggleRequestValue(filters, props.field, mode, props.value)
  }
  // The result may have fewer pages than the page the dialog was opened from.
  if (urlState.page.value !== 1) urlState.page.value = 1
  emit('filtered')
}
</script>

<template>
  <span class="inline-flex shrink-0 items-center">
    <Button
      variant="ghost"
      size="sm"
      class="h-6 w-6 p-0"
      aria-label="Show only alerts with this value"
      title="Show only alerts with this value"
      @click="apply('include')"
    >
      <Icon name="lucide:filter" class="h-3 w-3" />
    </Button>
    <Button
      variant="ghost"
      size="sm"
      class="h-6 w-6 p-0"
      aria-label="Hide alerts with this value"
      title="Hide alerts with this value"
      @click="apply('exclude')"
    >
      <Icon name="lucide:ban" class="h-3 w-3" />
    </Button>
  </span>
</template>
