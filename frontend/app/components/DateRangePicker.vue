<template>
  <Popover v-model:open="open">
    <PopoverTrigger as-child>
      <Button
        variant="outline"
        class="min-w-[320px] justify-start text-left font-normal h-8 px-3 text-xs"
      >
        <Icon name="lucide:calendar" class="mr-2 h-3.5 w-3.5 flex-shrink-0" />
        <div class="flex items-center gap-2 flex-1">
          <template v-if="displayText">
            <span class="font-medium">{{ displayLabel }}</span>
            <span class="text-muted-foreground">•</span>
            <span class="text-muted-foreground">{{ displayText }}</span>
          </template>
          <template v-else>
            <span class="text-muted-foreground">Select date range</span>
          </template>
        </div>
      </Button>
    </PopoverTrigger>
    <PopoverContent class="w-auto p-0" align="start">
      <div class="flex">
        <div class="flex flex-col p-4 border-r min-w-[180px]">
          <h4 class="font-display text-sm font-semibold mb-2">Quick Select</h4>
          <div class="grid gap-1 overflow-y-auto pr-2 -mr-2 max-h-[370px]">
            <Button
              v-for="preset in DATE_PRESETS"
              :key="preset.id"
              :variant="currentPresetId === preset.id ? 'default' : 'ghost'"
              size="sm"
              class="justify-start text-xs h-8"
              @click="selectPreset(preset)"
            >
              {{ preset.label }}
            </Button>
          </div>
        </div>

        <div class="p-3">
          <RangeCalendar
            v-model="pickerValue"
            :number-of-months="2"
            locale="de-DE"
            :week-starts-on="1"
            @update:model-value="onCalendarChange"
          />

          <div v-if="includeTime" class="border-t pt-3 mt-3">
            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-1.5">
                <div class="flex items-center justify-between">
                  <Label class="text-xs font-medium text-muted-foreground">Start Time</Label>
                  <span class="text-xs text-muted-foreground">{{ startTime }}</span>
                </div>
                <Input
                  type="time"
                  :model-value="startTime"
                  class="h-8 text-xs"
                  step="60"
                  @change="onStartTimeChange"
                />
              </div>

              <div class="space-y-1.5">
                <div class="flex items-center justify-between">
                  <Label class="text-xs font-medium text-muted-foreground">
                    End Time
                    <span v-if="isRelativePreset(currentPresetId)" class="ml-1 text-[10px] opacity-60">(now)</span>
                  </Label>
                  <span class="text-xs text-muted-foreground">{{ endTime }}</span>
                </div>
                <Input
                  type="time"
                  :model-value="endTime"
                  class="h-8 text-xs"
                  step="60"
                  :disabled="isRelativePreset(currentPresetId)"
                  @change="onEndTimeChange"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </PopoverContent>
  </Popover>
</template>

<script setup lang="ts">
import type { DateRange } from 'reka-ui'
import { CalendarDate, CalendarDateTime, getLocalTimeZone } from '@internationalized/date'
import { DATE_PRESETS, isRelativePreset, isValidPresetId, getPresetLabel, type DatePreset, type DatePresetId } from '@/utils/datePresets'

interface DateRangeValue {
  from: Date | undefined
  to: Date | undefined
  presetId?: DatePresetId
}

const props = defineProps<{
  modelValue?: DateRangeValue
  includeTime?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: DateRangeValue]
}>()

// Reusable formatters (expensive to construct)
const dateFormatter = new Intl.DateTimeFormat('de-DE', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
})
const dateTimeFormatter = new Intl.DateTimeFormat('de-DE', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

const open = ref(false)

// Internal state
const pickerValue = ref<DateRange>({ start: undefined, end: undefined })
const startTime = ref('00:00')
const endTime = ref('23:59')

// Track last synced timestamps to avoid redundant updates
let lastSyncedFrom = 0
let lastSyncedTo = 0

// Current preset from modelValue only
const currentPresetId = computed<DatePresetId | null>(() => {
  const id = props.modelValue?.presetId
  return isValidPresetId(id) ? id : null
})

// Display label
const displayLabel = computed(() => {
  if (currentPresetId.value) return getPresetLabel(currentPresetId.value)
  if (props.modelValue?.from && props.modelValue?.to) return 'Custom'
  return null
})

// Format dates for display
const displayText = computed(() => {
  const from = props.modelValue?.from
  const to = props.modelValue?.to
  if (!from) return null

  const fmt = props.includeTime ? dateTimeFormatter : dateFormatter
  const fromStr = fmt.format(from)
  if (!to) return fromStr

  const endDate = isRelativePreset(currentPresetId.value) ? new Date() : to
  return `${fromStr} - ${fmt.format(endDate)}`
})

// Sync from modelValue only when timestamps actually change
watch(
  () => [props.modelValue?.from?.getTime(), props.modelValue?.to?.getTime()] as const,
  ([fromTs, toTs]) => {
    if (!fromTs || !toTs) return
    if (fromTs === lastSyncedFrom && toTs === lastSyncedTo) return

    lastSyncedFrom = fromTs
    lastSyncedTo = toTs

    const from = props.modelValue!.from!
    const to = props.modelValue!.to!

    pickerValue.value = {
      start: toCalendarDate(from),
      end: toCalendarDate(to)
    }

    if (props.includeTime) {
      startTime.value = formatTime(from)
      endTime.value = formatTime(to)
    }
  },
  { immediate: true }
)

function toCalendarDate(date: Date) {
  return props.includeTime
    ? new CalendarDateTime(date.getFullYear(), date.getMonth() + 1, date.getDate(), date.getHours(), date.getMinutes())
    : new CalendarDate(date.getFullYear(), date.getMonth() + 1, date.getDate())
}

function formatTime(date: Date): string {
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function parseTime(time: string): { h: number; m: number } {
  const [h, m] = time.split(':').map(Number)
  return { h: h || 0, m: m || 0 }
}

function onCalendarChange(range: DateRange) {
  if (!range.start || !range.end) return

  const start = parseTime(startTime.value)
  const end = parseTime(endTime.value)

  const from = range.start.toDate(getLocalTimeZone())
  const to = range.end.toDate(getLocalTimeZone())

  if (props.includeTime) {
    from.setHours(start.h, start.m, 0, 0)
    to.setHours(end.h, end.m, 59, 999)
  }

  emit('update:modelValue', { from, to }) // No presetId = custom
}

function onStartTimeChange(e: Event) {
  const value = (e.target as HTMLInputElement).value
  startTime.value = value
  emitWithCurrentDates()
}

function onEndTimeChange(e: Event) {
  const value = (e.target as HTMLInputElement).value
  endTime.value = value
  emitWithCurrentDates()
}

function emitWithCurrentDates() {
  if (!pickerValue.value.start || !pickerValue.value.end) return

  const start = parseTime(startTime.value)
  const end = parseTime(endTime.value)

  const from = pickerValue.value.start.toDate(getLocalTimeZone())
  const to = pickerValue.value.end.toDate(getLocalTimeZone())

  if (props.includeTime) {
    from.setHours(start.h, start.m, 0, 0)
    to.setHours(end.h, end.m, 59, 999)
  }

  emit('update:modelValue', { from, to })
}

function selectPreset(preset: DatePreset) {
  const { from, to } = preset.computeRange()

  pickerValue.value = {
    start: toCalendarDate(from),
    end: toCalendarDate(to)
  }

  if (props.includeTime) {
    startTime.value = formatTime(from)
    endTime.value = formatTime(to)
  }

  emit('update:modelValue', { from, to, presetId: preset.id })
  open.value = false
}
</script>
