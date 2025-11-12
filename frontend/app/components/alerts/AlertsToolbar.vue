<template>
  <div class="flex items-center justify-between pb-2">
    <div class="flex items-center gap-3">
      <!-- Back to groups when drilled into ungrouped filtered view -->
      <Button
        v-if="isDrilldown"
        variant="ghost"
        size="sm"
        class="-ml-1 px-2"
        aria-label="Back to groups"
        @click="backToGroups"
      >
        <Icon name="lucide:arrow-left" class="mr-1 h-4 w-4" />
        Back to groups
      </Button>
      <div class="relative">
        <Icon name="lucide:search" class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          class="h-9 w-72 pl-9 pr-3 border-border bg-background/50 focus:bg-background transition-colors"
          placeholder="Filter alerts by classification..."
          :model-value="urlState.filters.value.classification_text || ''"
          @update:model-value="handleSearchFilter"
        />
      </div>
      
      <DateRangePicker
        v-model="dateRange"
        :includeTime="true"
      />
    </div>
    
    <div class="flex items-center gap-2">
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button
            variant="outline"
            size="sm"
            class="h-8 px-3 text-xs font-medium border-border hover:bg-background transition-all"
          >
            <Icon 
              :name="autoRefreshEnabled ? 'lucide:clock' : 'lucide:pause'" 
              class="mr-2 h-3.5 w-3.5"
            />
            {{ autoRefreshDisplayText }}
            <Icon name="lucide:chevron-down" class="ml-1 h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Auto-refresh interval</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            @click="setAutoRefresh(0)"
            :class="urlState.autoRefresh.value === 0 ? 'bg-accent' : ''"
          >
            <Icon name="lucide:pause" class="mr-2 h-4 w-4" />
            Inactive
          </DropdownMenuItem>
          <DropdownMenuItem
            @click="setAutoRefresh(30)"
            :class="urlState.autoRefresh.value === 30 ? 'bg-accent' : ''"
          >
            <Icon name="lucide:clock" class="mr-2 h-4 w-4" />
            30 seconds
          </DropdownMenuItem>
          <DropdownMenuItem
            @click="setAutoRefresh(60)"
            :class="urlState.autoRefresh.value === 60 ? 'bg-accent' : ''"
          >
            <Icon name="lucide:clock" class="mr-2 h-4 w-4" />
            1 minute
          </DropdownMenuItem>
          <DropdownMenuItem
            @click="setAutoRefresh(300)"
            :class="urlState.autoRefresh.value === 300 ? 'bg-accent' : ''"
          >
            <Icon name="lucide:clock" class="mr-2 h-4 w-4" />
            5 minutes
          </DropdownMenuItem>
          <DropdownMenuItem
            @click="setAutoRefresh(600)"
            :class="urlState.autoRefresh.value === 600 ? 'bg-accent' : ''"
          >
            <Icon name="lucide:clock" class="mr-2 h-4 w-4" />
            10 minutes
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      
      <ClientOnly>
        <Button
          variant="outline"
          size="sm"
          @click="$emit('toggleView')"
          class="h-8 px-3 text-xs font-medium border-border hover:bg-background transition-all"
          :disabled="pending"
        >
          <Icon v-if="!isGrouped" name="lucide:users" class="mr-2 h-3.5 w-3.5" />
          <Icon v-else name="lucide:list" class="mr-2 h-3.5 w-3.5" />
          {{ isGrouped ? 'Show Individual' : 'Group by IP' }}
        </Button>
        <template #fallback>
          <Button
            variant="outline"
            size="sm"
            class="h-8 px-3 text-xs font-medium border-border hover:bg-background transition-all"
          >
            <Icon v-if="!isGrouped" name="lucide:users" class="mr-2 h-3.5 w-3.5" />
            <Icon v-else name="lucide:list" class="mr-2 h-3.5 w-3.5" />
            {{ isGrouped ? 'Show Individual' : 'Group by IP' }}
          </Button>
        </template>
      </ClientOnly>
      
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button variant="outline" size="sm" class="h-8 px-3 text-xs font-medium border-border hover:bg-background">
            <Icon name="lucide:columns" class="mr-2 h-3.5 w-3.5" />
            Columns <Icon name="lucide:chevron-down" class="ml-1 h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuCheckboxItem
            v-for="column in table.getAllColumns().filter((column) => column.getCanHide())"
            :key="column.id"
            class="capitalize"
            :model-value="column.getIsVisible()"
            @update:model-value="(value) => column.toggleVisibility(!!value)"
          >
            {{ column.id }}
          </DropdownMenuCheckboxItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Button
        v-if="!isGrouped"
        variant="destructive"
        size="sm"
        class="h-8 px-3 text-xs font-medium"
        :disabled="!canBulkDelete || pending"
        @click="$emit('bulkDelete')"
      >
        <Icon name="lucide:trash-2" class="mr-2 h-3.5 w-3.5" />
        Delete selected
        <span v-if="selectionCount" class="ml-2 rounded bg-destructive-foreground/10 px-1.5 py-0.5 text-[10px] font-semibold text-destructive-foreground">
          {{ selectionCount }}
        </span>
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DropdownMenuCheckboxItemProps } from 'reka-ui'
import { useDebounceFn } from '@vueuse/core'
import { getPresetRange, isRelativePreset, isValidPresetId, type DatePresetId } from '@/utils/datePresets'
import DateRangePicker from '@/components/DateRangePicker.vue'
import { useAlertTableContext } from '@/composables/useAlertTableContext'

interface DateRangeValue {
  from: Date | undefined
  to: Date | undefined
  presetId?: DatePresetId
}

interface Emits {
  toggleView: []
  startAutoRefresh: []
  stopAutoRefresh: []
  bulkDelete: []
}

const emit = defineEmits<Emits>()

const { urlState, table, isGrouped, pending, relativeRefreshToken } = useAlertTableContext()
const route = useRoute()

// Detect drilldown: ungrouped view with any of the deep-link filters present
const isDrilldown = computed(() => {
  const f = urlState.filters.value
  return !isGrouped.value && (Boolean(f.classification_text) || Boolean(f.source_ipv4) || Boolean(f.target_ipv4))
})

// Use TanStack Table's built-in selection API
const selectionCount = computed(() => table.getSelectedRowModel().rows.length)

const canBulkDelete = computed(() => !isGrouped.value && selectionCount.value > 0)

async function backToGroups() {
  // Build a single navigation update to avoid racing URL pushes
  const { classification_text, source_ipv4, target_ipv4, ...rest } = urlState.filters.value
  const newQuery: Record<string, any> = {
    ...route.query,
    view: 'grouped',
    sort: 'total_count:desc',
    page: '1',
    filter: Object.keys(rest).length > 0 ? JSON.stringify(rest) : undefined,
  }
  // Remove empty values
  Object.keys(newQuery).forEach((k) => {
    if (newQuery[k] === '' || newQuery[k] === null || newQuery[k] === undefined) {
      delete newQuery[k]
    }
  })
  await navigateTo({ query: newQuery })
}

const dateRange = computed<DateRangeValue>({
  get: () => {
    const filters = urlState.filters.value
    const presetId = filters.date_preset as string | undefined

    if (isValidPresetId(presetId)) {
      relativeRefreshToken.value // Track dependency for relative preset updates
      const { from, to } = getPresetRange(presetId)
      return { from, to, presetId }
    }

    const from = filters.start_date ? new Date(filters.start_date as string) : undefined
    const to = filters.end_date ? new Date(filters.end_date as string) : undefined

    if (from && to) {
      return { from, to }
    }

    const { from: defaultFrom, to: defaultTo } = getPresetRange('last-24-hours')
    return { from: defaultFrom, to: defaultTo, presetId: 'last-24-hours' as DatePresetId }
  },
  set: (value: DateRangeValue) => {
    const nextFilters: Record<string, string | number> = { ...urlState.filters.value }

    delete nextFilters.start_date
    delete nextFilters.end_date
    delete nextFilters.date_preset

    if (value.presetId && isValidPresetId(value.presetId)) {
      const presetId = value.presetId as DatePresetId
      const { from, to } = getPresetRange(presetId)

      if (isRelativePreset(presetId)) {
        delete nextFilters.start_date
        delete nextFilters.end_date
      } else {
        nextFilters.start_date = from.toISOString()
        nextFilters.end_date = to.toISOString()
      }

      nextFilters.date_preset = presetId
    } else if (value.from && value.to) {
      nextFilters.start_date = value.from.toISOString()
      nextFilters.end_date = value.to.toISOString()
    }

    urlState.filters.value = nextFilters
  }
})

const autoRefreshEnabled = computed(() => urlState.autoRefresh.value > 0)

const autoRefreshDisplayText = computed(() => {
  if (!autoRefreshEnabled.value) return 'Off'
  const value = urlState.autoRefresh.value
  return value >= 60 ? `${value / 60}m` : `${value}s`
})

const updateSearchFilter = (value: string | number) => {
  const stringValue = String(value)
  if (stringValue) {
    urlState.filters.value = { 
      ...urlState.filters.value, 
      classification_text: stringValue 
    }
  } else {
    const { classification_text, ...rest } = urlState.filters.value
    urlState.filters.value = rest
  }
}

const handleSearchFilter = useDebounceFn(updateSearchFilter, 300)

function setAutoRefresh(seconds: number) {
  urlState.autoRefresh.value = seconds
  if (seconds === 0) {
    emit('stopAutoRefresh')
  } else {
    emit('startAutoRefresh')
  }
}
</script>
