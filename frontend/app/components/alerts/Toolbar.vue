<template>
  <div class="flex items-center justify-between">
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
        <AlertsDateRangePicker
          v-model="dateRange"
          :includeTime="true"
        />
        <AlertsFilterPanel />
      </div>

      <div class="flex items-center gap-2">
        <!-- Live/Pause Toggle Button with Connection Status -->
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                variant="outline"
                size="sm"
                class="h-8 px-3 text-xs font-medium"
                @click="toggleLive"
              >
                <!-- Paused: user disabled live mode -->
                <template v-if="!isLive">
                  <Icon name="lucide:pause" class="mr-2 size-4 text-muted-foreground" />
                  Paused
                </template>
                <!-- Live + Connected: green pulsing dot -->
                <template v-else-if="sseStatus === 'OPEN'">
                  <span class="mr-2 size-2 rounded-full bg-green-500 animate-pulse" />
                  Live
                </template>
                <!-- Live + Connecting: yellow spinner -->
                <template v-else-if="sseStatus === 'CONNECTING'">
                  <Icon name="lucide:loader-2" class="mr-2 size-4 text-yellow-500 animate-spin" />
                  Connecting
                </template>
                <!-- Live + Closed/Error: red dot with reconnecting state -->
                <template v-else>
                  <span class="mr-2 size-2 rounded-full bg-red-500" />
                  Offline
                </template>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom" :side-offset="4">
              <template v-if="!isLive">
                Click to enable real-time updates
              </template>
              <template v-else-if="sseStatus === 'OPEN'">
                Connected - receiving live updates
              </template>
              <template v-else-if="sseStatus === 'CONNECTING'">
                Establishing connection...
              </template>
              <template v-else-if="sseError">
                Connection error - will retry automatically
              </template>
              <template v-else>
                Disconnected - will retry automatically
              </template>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

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
interface DateRangeValue {
  from: Date | undefined
  to: Date | undefined
  presetId?: DatePresetId
}

type SseStatus = 'CONNECTING' | 'OPEN' | 'CLOSED'

interface Props {
  isLive?: boolean
  sseStatus?: SseStatus
  sseError?: Event | null
}

interface Emits {
  toggleView: []
  toggleLive: []
  bulkDelete: []
  refresh: []
}

const props = withDefaults(defineProps<Props>(), {
  isLive: false,
  sseStatus: 'CLOSED',
  sseError: null,
})

const emit = defineEmits<Emits>()

const { urlState, table, isGrouped, pending, relativeRefreshToken } = useAlertTableContext()
const route = useRoute()

function toggleLive() {
  emit('toggleLive')
}

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
    sort: 'detected_at:desc',
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

// Separate ref to hold stable object reference (prevents re-render loops)
const dateRangeRef = shallowRef<DateRangeValue>({ from: undefined, to: undefined })

// Update dateRangeRef when filters change
watchEffect(() => {
  const filters = urlState.filters.value
  const presetId = filters.date_preset as string | undefined
  relativeRefreshToken.value // track for relative preset refresh

  if (isValidPresetId(presetId)) {
    const { from, to } = getPresetRange(presetId)
    dateRangeRef.value = { from, to, presetId }
  } else if (filters.start_date && filters.end_date) {
    dateRangeRef.value = {
      from: new Date(filters.start_date as string),
      to: new Date(filters.end_date as string)
    }
  } else {
    const { from, to } = getPresetRange('last-24-hours')
    dateRangeRef.value = { from, to, presetId: 'last-24-hours' as DatePresetId }
  }
})

// v-model binding - getter returns stable ref, setter updates URL
const dateRange = computed<DateRangeValue>({
  get: () => dateRangeRef.value,
  set: (value: DateRangeValue) => {
    const nextFilters: Record<string, string | number> = { ...urlState.filters.value }

    delete nextFilters.start_date
    delete nextFilters.end_date
    delete nextFilters.date_preset

    if (value.presetId && isValidPresetId(value.presetId)) {
      const presetId = value.presetId as DatePresetId
      if (!isRelativePreset(presetId)) {
        const { from, to } = getPresetRange(presetId)
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
</script>
