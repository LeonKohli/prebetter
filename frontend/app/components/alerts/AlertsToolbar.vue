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
          <Icon name="lucide:arrow-left" class="mr-1 size-4" />
          Back to groups
        </Button>
      <InputGroup class="w-72 h-8">
        <InputGroupAddon>
          <Icon name="lucide:search" class="size-4" />
        </InputGroupAddon>
        <InputGroupInput
          class="text-xs"
          placeholder="Filter alerts by classification..."
          :model-value="urlState.filters.value.classification_text || ''"
          @update:model-value="handleSearchFilter"
        />
      </InputGroup>
        
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
              class="h-8 px-3 text-xs font-medium"
            >
              <Icon 
                :name="autoRefreshEnabled ? 'lucide:clock' : 'lucide:pause'" 
                class="mr-2 size-4"
              />
              {{ autoRefreshDisplayText }}
              <Icon name="lucide:chevron-down" class="ml-1 h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Auto-refresh interval</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuRadioGroup
              :model-value="autoRefreshModel"
              @update:model-value="handleAutoRefreshChange"
            >
              <DropdownMenuRadioItem
                v-for="option in autoRefreshOptions"
                :key="option.value"
                :value="option.value"
                class="flex items-center"
              >
                <Icon :name="option.icon" class="mr-2 size-4" />
                {{ option.label }}
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
        
        <ClientOnly>
          <Button
            variant="outline"
            size="sm"
            @click="$emit('toggleView')"
            class="h-8 px-3 text-xs font-medium"
            :disabled="pending"
          >
            <Icon v-if="!isGrouped" name="lucide:users" class="mr-2 size-4" />
            <Icon v-else name="lucide:list" class="mr-2 size-4" />
            {{ isGrouped ? 'Show Individual' : 'Group by IP' }}
          </Button>
          <template #fallback>
            <Button
              variant="outline"
              size="sm"
              class="h-8 px-3 text-xs font-medium"
            >
              <Icon v-if="!isGrouped" name="lucide:users" class="mr-2 size-4" />
              <Icon v-else name="lucide:list" class="mr-2 size-4" />
              {{ isGrouped ? 'Show Individual' : 'Group by IP' }}
            </Button>
          </template>
        </ClientOnly>
        
        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button variant="outline" size="sm" class="h-8 px-3 text-xs font-medium">
              <Icon name="lucide:columns" class="mr-2 size-4" />
              Columns <Icon name="lucide:chevron-down" class="ml-1 h-3.5 w-3.5" />
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
      </div>
  </div>
</template>

<script setup lang="ts">
import type { DropdownMenuCheckboxItemProps } from 'reka-ui'
import { useDebounceFn } from '@vueuse/core'
import { getPresetRange, isRelativePreset, isValidPresetId, type DatePresetId } from '@/utils/datePresets'
import DateRangePicker from '@/components/DateRangePicker.vue'
import { useAlertTableContext } from '@/composables/useAlertTableContext'
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/components/ui/input-group'

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

async function backToGroups() {
  // Build a single navigation update to avoid racing URL pushes
  const { classification_text, source_ipv4, target_ipv4, ...rest } = urlState.filters.value
  const newQuery: Record<string, any> = {
    ...route.query,
    view: 'grouped',
    sort: 'detected_at:desc', // Changed from 'total_count:desc' to match default sort order
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

const autoRefreshOptions = [
  { value: '0', label: 'Inactive', icon: 'lucide:pause' },
  { value: '30', label: '30 seconds', icon: 'lucide:clock' },
  { value: '60', label: '1 minute', icon: 'lucide:clock' },
  { value: '300', label: '5 minutes', icon: 'lucide:clock' },
  { value: '600', label: '10 minutes', icon: 'lucide:clock' },
] as const

const autoRefreshModel = computed(() => String(urlState.autoRefresh.value ?? 0))

const autoRefreshEnabled = computed(() => Number(autoRefreshModel.value) > 0)

const autoRefreshDisplayText = computed(() => {
  if (!autoRefreshEnabled.value) return 'Off'
  const value = Number(autoRefreshModel.value)
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

function handleAutoRefreshChange(value: string) {
  const seconds = Number.parseInt(value, 10)
  if (Number.isNaN(seconds)) return
  setAutoRefresh(seconds)
}
</script>
