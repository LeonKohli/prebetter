<script setup lang="ts">
import type { RequestFilterField } from '~~/shared/types/alerts'
import { requestFilterValues, toggleRequestValue, type RequestFilterMode } from '@/utils/requestFilters'

/**
 * One header of the alert's HTTP request as a filter: the most common values in the current range to
 * show or to hide. A value is shown (check) or hidden (crossed out), never both.
 */
const props = defineProps<{
  field: RequestFilterField
  label: string
  icon: string
  placeholder: string
}>()

const { urlState } = useAlertTableContext()
const { values, status, error, search, load } = useRequestValues(props.field)

const open = ref(false)

const shown = computed(() => requestFilterValues(urlState.filters.value, props.field, 'include'))
const hidden = computed(() => requestFilterValues(urlState.filters.value, props.field, 'exclude'))

function toggle(mode: RequestFilterMode, value: string) {
  urlState.filters.value = toggleRequestValue(urlState.filters.value, props.field, mode, value)
}

// Values that are set but not among the suggestions stay in the list, so they can be taken out again.
const rows = computed(() => {
  const counts = new Map(values.value.map(v => [v.value, v.count]))
  const known = new Set([...shown.value, ...hidden.value])
  const text = search.value.trim().toLowerCase()
  const selected = [...shown.value, ...hidden.value].filter(v => !text || v.toLowerCase().includes(text))
  const others = values.value.filter(v => !known.has(v.value)).map(v => v.value)
  return [...selected, ...others].map(value => ({
    value,
    count: counts.get(value),
    mode: shown.value.includes(value) ? 'include' as const : hidden.value.includes(value) ? 'exclude' as const : null,
  }))
})

const summary = computed(() => {
  if (shown.value.length === 1 && !hidden.value.length) return shown.value[0]!
  if (hidden.value.length === 1 && !shown.value.length) return `not ${hidden.value[0]!}`
  const parts = []
  if (shown.value.length) parts.push(`${shown.value.length} shown`)
  if (hidden.value.length) parts.push(`${hidden.value.length} hidden`)
  return parts.join(', ')
})

watch(open, (isOpen) => {
  if (isOpen) void load()
  else search.value = ''
})

// Typing narrows the suggestions on the server; the first load is the open above.
watch(search, () => {
  if (open.value) void load()
})
</script>

<template>
  <div class="space-y-1.5">
    <Label class="text-xs">{{ label }}</Label>
    <Popover v-model:open="open">
      <PopoverTrigger as-child>
        <Button variant="outline" role="combobox" class="w-full justify-between font-normal">
          <div class="flex items-center gap-2 truncate">
            <Icon :name="icon" class="size-4 shrink-0 text-muted-foreground" />
            <span v-if="!summary" class="text-muted-foreground">Any</span>
            <span v-else class="truncate">{{ summary }}</span>
          </div>
          <Icon name="lucide:chevron-down" class="size-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent class="w-80 p-0" align="start">
        <div class="flex h-9 items-center gap-2 border-b px-3">
          <Icon name="lucide:search" class="size-4 shrink-0 opacity-50" />
          <input
            v-model="search"
            :placeholder="placeholder"
            :aria-label="`Search ${label.toLowerCase()}`"
            maxlength="100"
            class="placeholder:text-muted-foreground flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-none"
          >
        </div>
        <div v-if="error" class="py-6 text-center text-sm text-destructive">
          Could not load the values.
        </div>
        <div v-else-if="status === 'pending' && !rows.length" class="py-6 text-center text-sm text-muted-foreground">
          Loading...
        </div>
        <div v-else-if="!rows.length" class="px-4 py-6 text-center text-sm text-muted-foreground">
          No requests in this range.
        </div>
        <div v-else class="max-h-64 overflow-auto p-1">
          <div
            v-for="row in rows"
            :key="row.value"
            class="flex min-h-8 items-center gap-2 rounded-sm px-2 py-1 text-sm hover:bg-accent hover:text-accent-foreground"
          >
            <button
              type="button"
              class="flex min-w-0 flex-1 cursor-pointer items-center gap-2 text-left outline-none"
              :aria-label="`${row.mode === 'include' ? 'Stop showing' : 'Show only'} ${row.value}`"
              @click="toggle('include', row.value)"
            >
              <Checkbox :model-value="row.mode === 'include'" class="pointer-events-none shrink-0" tabindex="-1" />
              <span
                class="min-w-0 break-all"
                :class="row.mode === 'exclude' ? 'text-muted-foreground line-through' : ''"
                :title="row.value"
              >{{ row.value }}</span>
            </button>
            <span v-if="row.count !== undefined" class="shrink-0 text-xs tabular-nums text-muted-foreground">{{ row.count }}</span>
            <Button
              variant="ghost"
              size="sm"
              class="size-6 shrink-0 p-0"
              :class="row.mode === 'exclude' ? 'text-primary' : 'text-muted-foreground'"
              :aria-label="`${row.mode === 'exclude' ? 'Stop hiding' : 'Hide'} ${row.value}`"
              :title="row.mode === 'exclude' ? 'Stop hiding' : 'Hide alerts with this value'"
              @click="toggle('exclude', row.value)"
            >
              <Icon name="lucide:ban" class="size-3.5" />
            </Button>
          </div>
        </div>
        <p class="border-t px-3 py-2 text-xs text-muted-foreground">
          Only alerts with a recorded HTTP request have these values. The client's own headers, so advisory.
        </p>
      </PopoverContent>
    </Popover>
  </div>
</template>
