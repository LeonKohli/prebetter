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
            <template v-if="activePresetLabel">
              <span class="font-medium">{{ activePresetLabel }}</span>
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
              :key="preset.label"
              :variant="activePresetLabel === preset.label ? 'default' : 'ghost'"
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
            v-model="value" 
            :number-of-months="2"
            locale="de-DE"
            :week-starts-on="1"
            class="[&_[data-selection-start]:hover]:!bg-primary [&_[data-selection-start]:hover]:!text-primary-foreground [&_[data-selection-end]:hover]:!bg-primary [&_[data-selection-end]:hover]:!text-primary-foreground"
            @update:start-value="(startDate) => value.start = startDate"
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
}

interface QuickPreset {
  label: string
  getValue: () => DateRange
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

const activePreset = computed(() => {
  if (!props.modelValue?.from || !props.modelValue?.to) {
    return null
  }
  
  // Simple matching - check each preset and see if dates match (ignoring seconds/milliseconds)
  for (const preset of quickPresets) {
    const presetRange = preset.getValue()
    if (presetRange.start && presetRange.end) {
      const presetFrom = presetRange.start.toDate(getLocalTimeZone())
      const presetTo = presetRange.end.toDate(getLocalTimeZone())
      
      // Compare dates at minute precision (ignore seconds)
      const fromMatches = 
        props.modelValue.from.getFullYear() === presetFrom.getFullYear() &&
        props.modelValue.from.getMonth() === presetFrom.getMonth() &&
        props.modelValue.from.getDate() === presetFrom.getDate() &&
        props.modelValue.from.getHours() === presetFrom.getHours() &&
        Math.abs(props.modelValue.from.getMinutes() - presetFrom.getMinutes()) <= 1
      
      const toMatches = 
        props.modelValue.to.getFullYear() === presetTo.getFullYear() &&
        props.modelValue.to.getMonth() === presetTo.getMonth() &&
        props.modelValue.to.getDate() === presetTo.getDate() &&
        props.modelValue.to.getHours() === presetTo.getHours() &&
        Math.abs(props.modelValue.to.getMinutes() - presetTo.getMinutes()) <= 1
      
      if (fromMatches && toMatches) {
        return preset
      }
    }
  }
  
  return null
})

const activePresetLabel = computed(() => activePreset.value?.label || null)

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
  if (!value.value?.start) return null
  
  const formatter = props.includeTime ? dtf : df
  const startStr = formatter.format(value.value.start.toDate(getLocalTimeZone()))
  
  if (!value.value.end) {
    return startStr
  }
  
  const endStr = formatter.format(value.value.end.toDate(getLocalTimeZone()))
  return `${startStr} - ${endStr}`
})

// Convert between Date and CalendarDate/CalendarDateTime
const value = computed<DateRange>({
  get: () => {
    const from = props.modelValue?.from
    const to = props.modelValue?.to
    
    if (!from) {
      return {
        start: undefined,
        end: undefined,
      } as DateRange
    }
    
    // Update time refs when value changes
    if (from && props.includeTime) {
      startHour.value = String(from.getHours()).padStart(2, '0')
      startMinute.value = String(from.getMinutes()).padStart(2, '0')
    }
    if (to && props.includeTime) {
      endHour.value = String(to.getHours()).padStart(2, '0')
      endMinute.value = String(to.getMinutes()).padStart(2, '0')
    }
    
    const start = props.includeTime 
      ? dateToCalendarDateTime(from)
      : dateToCalendarDate(from)
    
    const end = to 
      ? (props.includeTime 
          ? dateToCalendarDateTime(to)
          : dateToCalendarDate(to))
      : undefined
    
    return {
      start,
      end,
    } as DateRange
  },
  set: (dateRange) => {
    let from: Date | undefined = undefined
    let to: Date | undefined = undefined
    
    if (dateRange.start) {
      const baseDate = dateRange.start.toDate(getLocalTimeZone())
      if (props.includeTime) {
        from = new Date(baseDate)
        
        // Check if the CalendarDateTime has time information (from presets or manual selection)
        const hasTimeInfo = 'hour' in dateRange.start
        
        if (hasTimeInfo && dateRange.start instanceof CalendarDateTime) {
          // Use the time from the CalendarDateTime (e.g., from hour presets)
          startHour.value = String(dateRange.start.hour).padStart(2, '0')
          startMinute.value = String(dateRange.start.minute || 0).padStart(2, '0')
        } else if (!props.modelValue?.from || baseDate.toDateString() !== props.modelValue.from.toDateString()) {
          // Only reset to defaults if it's a new date and no time info provided
          startHour.value = DEFAULT_START_HOUR
          startMinute.value = DEFAULT_START_MINUTE
        }
        
        from.setHours(parseInt(startHour.value), parseInt(startMinute.value))
      } else {
        from = baseDate
      }
    }
    
    if (dateRange.end) {
      const baseDate = dateRange.end.toDate(getLocalTimeZone())
      if (props.includeTime) {
        to = new Date(baseDate)
        
        // Check if the CalendarDateTime has time information
        const hasTimeInfo = 'hour' in dateRange.end
        
        if (hasTimeInfo && dateRange.end instanceof CalendarDateTime) {
          // Use the time from the CalendarDateTime
          endHour.value = String(dateRange.end.hour).padStart(2, '0')
          endMinute.value = String(dateRange.end.minute || 0).padStart(2, '0')
        } else if (!props.modelValue?.to || baseDate.toDateString() !== props.modelValue.to.toDateString()) {
          // Only reset to defaults if it's a new date and no time info provided
          endHour.value = DEFAULT_END_HOUR
          endMinute.value = DEFAULT_END_MINUTE
        }
        
        to.setHours(parseInt(endHour.value), parseInt(endMinute.value))
      } else {
        to = baseDate
      }
    }
    
    emit('update:modelValue', { from, to })
  }
})

watch([startHour, startMinute, endHour, endMinute], () => {
  if (props.includeTime && value.value.start) {
    value.value = { ...value.value }
  }
})

const todayDate = today(getLocalTimeZone())
const nowDateTime = now(getLocalTimeZone())

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
function createDayRangePreset(label: string, subtract: any): QuickPreset {
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
    label: 'Today',
    getValue: () => ({
      start: toCalendarDateTime(todayDate),
      end: toCalendarDateTime(todayDate, new Time(23, 59, 59))
    } as DateRange)
  },
  // Hour-based presets
  {
    label: 'Last Hour',
    getValue: createHourPreset(1)
  },
  {
    label: 'Last 2 Hours',
    getValue: createHourPreset(2)
  },
  // Current period presets
  {
    label: 'This Week',
    getValue: () => ({
      start: toCalendarDateTime(rekaStartOfWeek(todayDate, 'de-DE')),
      end: toCalendarDateTime(rekaEndOfWeek(todayDate, 'de-DE'), new Time(23, 59, 59))
    } as DateRange)
  },
  {
    label: 'This Month',
    getValue: () => ({
      start: toCalendarDateTime(rekaStartOfMonth(todayDate)),
      end: toCalendarDateTime(rekaEndOfMonth(todayDate), new Time(23, 59, 59))
    } as DateRange)
  },
  {
    label: 'This Year', 
    getValue: () => ({
      start: toCalendarDateTime(rekaStartOfYear(todayDate)),
      end: toCalendarDateTime(rekaEndOfYear(todayDate), new Time(23, 59, 59))
    } as DateRange)
  },
  // Day-based presets
  createDayRangePreset('Last 2 Days', { days: 2 }),
  createDayRangePreset('Last 7 Days', { days: 7 }),
  createDayRangePreset('Last 30 Days', { days: 30 }),
  createDayRangePreset('Last 3 Months', { months: 3 }),
  createDayRangePreset('Last 6 Months', { months: 6 }),
  createDayRangePreset('Last Year', { years: 1 })
]

function selectPreset(preset: QuickPreset) {
  const dateRange = preset.getValue()
  
  // Update time refs from the preset's CalendarDateTime objects
  if (props.includeTime && dateRange.start && dateRange.start instanceof CalendarDateTime) {
    startHour.value = String(dateRange.start.hour).padStart(2, '0')
    startMinute.value = String(dateRange.start.minute || 0).padStart(2, '0')
  }
  if (props.includeTime && dateRange.end && dateRange.end instanceof CalendarDateTime) {
    endHour.value = String(dateRange.end.hour).padStart(2, '0')
    endMinute.value = String(dateRange.end.minute || 0).padStart(2, '0')
  }
  
  value.value = dateRange
  open.value = false
}

// No complex watchers needed - the computed property handles everything!
</script>