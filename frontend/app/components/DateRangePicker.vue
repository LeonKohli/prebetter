<template>
  <Popover v-model:open="open">
    <PopoverTrigger as-child>
      <Button
        variant="outline"
        class="min-w-[320px] justify-start text-left font-normal h-8 px-3 text-xs border-border hover:bg-background transition-all"
      >
        <Icon name="lucide:calendar" class="mr-2 h-3.5 w-3.5 flex-shrink-0" />
        <div class="flex items-center gap-2 flex-1">
          <template v-if="formattedDateRange">
            <template v-if="displayLabel">
              <span class="font-medium">{{ displayLabel }}</span>
              <span class="text-muted-foreground">•</span>
            </template>
            
            <span class="text-muted-foreground">{{ formattedDateRange }}</span>
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
          <h4 class="text-sm font-semibold mb-2">Quick Select</h4>
          <div class="grid gap-1 overflow-y-auto pr-2 -mr-2 max-h-[370px]">
            <Button
              v-for="preset in quickPresets"
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
            class="[&_[data-selection-start]:hover]:!bg-primary [&_[data-selection-start]:hover]:!text-primary-foreground [&_[data-selection-end]:hover]:!bg-primary [&_[data-selection-end]:hover]:!text-primary-foreground"
            @update:start-value="(startDate) => pickerValue.start = startDate"
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
                  v-model="startTime"
                  class="h-8 text-xs"
                  step="60"
                  lang="de-DE"
                />
              </div>
              
              <div class="space-y-1.5">
                <div class="flex items-center justify-between">
                  <Label class="text-xs font-medium text-muted-foreground">End Time</Label>
                  <span class="text-xs text-muted-foreground">{{ endTime }}</span>
                </div>
                <Input 
                  type="time" 
                  v-model="endTime"
                  class="h-8 text-xs"
                  step="60"
                  lang="de-DE"
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
import { useNow } from '@vueuse/core'
import {
  CalendarDate,
  CalendarDateTime,
  DateFormatter,
  getLocalTimeZone,
  today,
  now,
  startOfWeek as rekaStartOfWeek,
  startOfMonth as rekaStartOfMonth,
  startOfYear as rekaStartOfYear,
  endOfWeek as rekaEndOfWeek,
  endOfMonth as rekaEndOfMonth,
  endOfYear as rekaEndOfYear,
  toCalendarDateTime,
  Time,
} from '@internationalized/date'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { RangeCalendar } from '@/components/ui/range-calendar'


interface DateRangeValue {
  from: Date | undefined
  to: Date | undefined
  // Track which preset was selected (optional, for stability)
  presetId?: string
}

interface QuickPreset {
  id: string
  label: string
  getValue: () => DateRange
  isRelative?: boolean
}

// Constants
const DEFAULT_START_HOUR = '00'
const DEFAULT_START_MINUTE = '00'
const DEFAULT_END_HOUR = '23'
const DEFAULT_END_MINUTE = '59'

const props = defineProps<{
  modelValue?: DateRangeValue
  includeTime?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: DateRangeValue]
}>()

const open = ref(false)

// Explicit picker state (avoids feedback loops from computed setter)
const pickerValue = ref<DateRange>({ start: undefined, end: undefined })

// Stable preset tracking: rely on an explicit presetId instead of
// reverse-matching against a moving "now()" window.
const selectedPresetId = ref<string | null>(null)

// Sync down from v-model if parent provides presetId (do not clear when undefined)
watch(
  () => props.modelValue?.presetId,
  (id) => {
    if (id != null) selectedPresetId.value = id
  },
  { immediate: true }
)

const currentPresetId = computed(() => props.modelValue?.presetId ?? selectedPresetId.value)
const selectedPreset = computed(() => quickPresets.find(p => p.id === currentPresetId.value) || null)
// Header label: preset label if present, otherwise 'Custom' when user selected a manual range
const displayLabel = computed(() => selectedPreset.value?.label || (pickerValue.value?.start ? 'Custom' : null))

// Time state - reactive refs
const startHour = ref(DEFAULT_START_HOUR)
const startMinute = ref(DEFAULT_START_MINUTE)
const endHour = ref(DEFAULT_END_HOUR)
const endMinute = ref(DEFAULT_END_MINUTE)

// Computed properties for v-model binding
const startTime = computed({
  get: () => `${startHour.value}:${startMinute.value}`,
  set: (value: string) => {
    const [h, m] = value.split(':')
    startHour.value = h || DEFAULT_START_HOUR
    startMinute.value = m || DEFAULT_START_MINUTE
  }
})

const endTime = computed({
  get: () => `${endHour.value}:${endMinute.value}`,
  set: (value: string) => {
    const [h, m] = value.split(':')
    endHour.value = h || DEFAULT_END_HOUR
    endMinute.value = m || DEFAULT_END_MINUTE
  }
})

// Use German locale for date/time formatting
const df = new DateFormatter('de-DE', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
})

const dtf = new DateFormatter('de-DE', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false, // Use 24-hour format
})

const formattedDateRange = computed(() => {
  if (!pickerValue.value?.start) return null
  
  const formatter = props.includeTime ? dtf : df
  const startStr = formatter.format(pickerValue.value.start.toDate(getLocalTimeZone()))
  
  if (!pickerValue.value.end) {
    return startStr
  }
  
  const endStr = formatter.format(pickerValue.value.end.toDate(getLocalTimeZone()))
  return `${startStr} - ${endStr}`
})

const isSyncingFromModel = ref(false)

function syncFromModel() {
  isSyncingFromModel.value = true
  const from = props.modelValue?.from
  const to = props.modelValue?.to

  // Update time inputs from model when provided
  if (props.includeTime && from) {
    startHour.value = String(from.getHours()).padStart(2, '0')
    startMinute.value = String(from.getMinutes()).padStart(2, '0')
  }
  if (props.includeTime && to) {
    endHour.value = String(to.getHours()).padStart(2, '0')
    endMinute.value = String(to.getMinutes()).padStart(2, '0')
  }

  // Build calendar values for the picker
  pickerValue.value = {
    start: from ? (props.includeTime ? dateToCalendarDateTime(from) : dateToCalendarDate(from)) : undefined,
    end: to ? (props.includeTime ? dateToCalendarDateTime(to) : dateToCalendarDate(to)) : undefined,
  }

  // Defer turning off the sync guard until the next tick so
  // any watchers observing pickerValue see the guard as active
  nextTick(() => { isSyncingFromModel.value = false })
}

// Init and keep in sync when modelValue changes
watch(
  () => [props.modelValue?.from?.getTime?.(), props.modelValue?.to?.getTime?.()].join('|'),
  () => syncFromModel(),
  { immediate: true }
)

function emitFromPicker(clearPreset = true) {
  // When updating from calendar/time, treat as manual unless explicitly from preset
  if (clearPreset) selectedPresetId.value = null

  let from: Date | undefined
  let to: Date | undefined

  const startVal = pickerValue.value.start
  const endVal = pickerValue.value.end

  if (startVal) {
    const base = startVal.toDate(getLocalTimeZone())
    if (props.includeTime) {
      from = new Date(base)
      const hasTimeInfo = 'hour' in startVal
      if (hasTimeInfo && startVal instanceof CalendarDateTime) {
        from.setHours(startVal.hour, startVal.minute || 0, 0, 0)
      } else {
        from.setHours(parseInt(startHour.value), parseInt(startMinute.value), 0, 0)
      }
    } else {
      from = base
    }
  }

  if (endVal) {
    const base = endVal.toDate(getLocalTimeZone())
    if (props.includeTime) {
      to = new Date(base)
      const hasTimeInfo = 'hour' in endVal
      if (hasTimeInfo && endVal instanceof CalendarDateTime) {
        to.setHours(endVal.hour, endVal.minute || 0, 59, 999)
      } else {
        to.setHours(parseInt(endHour.value), parseInt(endMinute.value), 59, 999)
      }
    } else {
      to = base
    }
  }

  emit('update:modelValue', { from, to, presetId: selectedPresetId.value || undefined })
}

// Emit when user changes calendar selection
watch(pickerValue, () => {
  if (!isSyncingFromModel.value) {
    emitFromPicker(!isSettingFromPreset.value)
  }
}, { deep: true })

watch([startHour, startMinute, endHour, endMinute], () => {
  if (props.includeTime && pickerValue.value.start && !isSyncingFromModel.value) {
    // Do not clear preset when the time inputs were set by a preset
    emitFromPicker(!isSettingFromPreset.value)
  }
})

const todayDate = today(getLocalTimeZone())

// Reactive current time using VueUse
const currentTime = useNow()

// Helper function to create hour-based presets with VueUse
function createHourPreset(hours: number): () => DateRange {
  return () => {
    const now = currentTime.value
    const hoursAgo = new Date(now.getTime() - hours * 60 * 60 * 1000)
    
    return {
      start: dateToCalendarDateTime(hoursAgo),
      end: dateToCalendarDateTime(now),
    } as DateRange
  }
}

// Helper function to convert Date to CalendarDateTime
function dateToCalendarDateTime(date: Date): CalendarDateTime {
  return new CalendarDateTime(
    date.getFullYear(),
    date.getMonth() + 1,
    date.getDate(),
    date.getHours(),
    date.getMinutes()
  )
}

// Helper function to convert Date to CalendarDate
function dateToCalendarDate(date: Date): CalendarDate {
  return new CalendarDate(
    date.getFullYear(),
    date.getMonth() + 1,
    date.getDate()
  )
}

// Helper to create day range presets with consistent times
function createDayRangePreset(label: string, subtract: any): Omit<QuickPreset, 'id' | 'isRelative'> {
  return {
    label,
    getValue: () => {
      const start = toCalendarDateTime(todayDate.subtract(subtract))
      const end = toCalendarDateTime(todayDate, new Time(23, 59, 59))
      return { start, end } as DateRange
    }
  }
}

const quickPresets: QuickPreset[] = [
  // Most common presets first
  {
    id: 'last-24-hours',
    label: 'Last 24 Hours',
    getValue: createHourPreset(24),
    isRelative: true,
  },
  {
    id: 'today',
    label: 'Today',
    getValue: () => ({
      start: toCalendarDateTime(todayDate),
      end: toCalendarDateTime(todayDate, new Time(23, 59, 59))
    } as DateRange),
    isRelative: false,
  },
  // Hour-based presets
  {
    id: 'last-1-hour',
    label: 'Last Hour',
    getValue: createHourPreset(1),
    isRelative: true,
  },
  {
    id: 'last-2-hours',
    label: 'Last 2 Hours',
    getValue: createHourPreset(2),
    isRelative: true,
  },
  // Current period presets
  {
    id: 'this-week',
    label: 'This Week',
    getValue: () => ({
      start: toCalendarDateTime(rekaStartOfWeek(todayDate, 'de-DE')),
      end: toCalendarDateTime(rekaEndOfWeek(todayDate, 'de-DE'), new Time(23, 59, 59))
    } as DateRange),
    isRelative: false,
  },
  {
    id: 'this-month',
    label: 'This Month',
    getValue: () => ({
      start: toCalendarDateTime(rekaStartOfMonth(todayDate)),
      end: toCalendarDateTime(rekaEndOfMonth(todayDate), new Time(23, 59, 59))
    } as DateRange),
    isRelative: false,
  },
  {
    id: 'this-year',
    label: 'This Year', 
    getValue: () => ({
      start: toCalendarDateTime(rekaStartOfYear(todayDate)),
      end: toCalendarDateTime(rekaEndOfYear(todayDate), new Time(23, 59, 59))
    } as DateRange),
    isRelative: false,
  },
  // Day-based presets
  { id: 'last-2-days', ...createDayRangePreset('Last 2 Days', { days: 2 }), isRelative: true },
  { id: 'last-7-days', ...createDayRangePreset('Last 7 Days', { days: 7 }), isRelative: true },
  { id: 'last-30-days', ...createDayRangePreset('Last 30 Days', { days: 30 }), isRelative: true },
  { id: 'last-3-months', ...createDayRangePreset('Last 3 Months', { months: 3 }), isRelative: true },
  { id: 'last-6-months', ...createDayRangePreset('Last 6 Months', { months: 6 }), isRelative: true },
  { id: 'last-year', ...createDayRangePreset('Last Year', { years: 1 }), isRelative: true },
]

// Guard to distinguish preset-driven updates from manual ones
const isSettingFromPreset = ref(false)

function selectPreset(preset: QuickPreset) {
  const dateRange = preset.getValue()
  selectedPresetId.value = preset.id
  // Guard subsequent reactive updates from being treated as manual edits
  isSettingFromPreset.value = true

  // Update time refs from the preset's CalendarDateTime objects BEFORE setting picker value
  if (props.includeTime && dateRange.start && dateRange.start instanceof CalendarDateTime) {
    startHour.value = String(dateRange.start.hour).padStart(2, '0')
    startMinute.value = String(dateRange.start.minute || 0).padStart(2, '0')
  }
  if (props.includeTime && dateRange.end && dateRange.end instanceof CalendarDateTime) {
    endHour.value = String(dateRange.end.hour).padStart(2, '0')
    endMinute.value = String(dateRange.end.minute || 0).padStart(2, '0')
  }

  nextTick(() => {
    pickerValue.value = dateRange
    // Emit model with preset preserved
    emitFromPicker(false)
    open.value = false
    // Allow a couple of flush cycles to settle before re-enabling manual detection
    nextTick(() => { isSettingFromPreset.value = false })
  })
}

// No complex watchers needed - the computed property handles everything!
</script>
