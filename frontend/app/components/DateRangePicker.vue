<template>
  <Popover v-model:open="open">
    <PopoverTrigger as-child>
      <Button
        variant="outline"
        class="min-w-[320px] justify-start text-left font-normal h-8 px-3 text-xs border-border hover:bg-background transition-all"
      >
        <Icon name="lucide:calendar" class="mr-2 h-3.5 w-3.5 flex-shrink-0" />
        <div class="flex items-center gap-2 flex-1">
          <template v-if="value?.start">
            <!-- Show active preset if applicable -->
            <template v-if="activePresetLabel">
              <span class="font-medium">{{ activePresetLabel }}</span>
              <span class="text-muted-foreground">•</span>
            </template>
            
            <!-- Show date range -->
            <span class="text-muted-foreground">
              <template v-if="value.end">
                <template v-if="includeTime">
                  {{ dtf.format(value.start.toDate(getLocalTimeZone())) }} - {{ dtf.format(value.end.toDate(getLocalTimeZone())) }}
                </template>
                <template v-else>
                  {{ df.format(value.start.toDate(getLocalTimeZone())) }} - {{ df.format(value.end.toDate(getLocalTimeZone())) }}
                </template>
              </template>
              <template v-else>
                <template v-if="includeTime">
                  {{ dtf.format(value.start.toDate(getLocalTimeZone())) }}
                </template>
                <template v-else>
                  {{ df.format(value.start.toDate(getLocalTimeZone())) }}
                </template>
              </template>
            </span>
          </template>
          <template v-else>
            <span class="text-muted-foreground">Pick a date range</span>
          </template>
        </div>
      </Button>
    </PopoverTrigger>
    <PopoverContent class="w-auto p-0" align="start">
      <div class="flex">
        <!-- Quick Presets -->
        <div class="flex flex-col p-4 border-r min-w-[180px] max-h-[430px]">
          <h4 class="text-sm font-semibold mb-2">Quick Select</h4>
          <div class="grid gap-1 overflow-y-auto pr-2 -mr-2">
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
        
        <!-- Range Calendar -->
        <div class="p-3">
          <RangeCalendar 
            v-model="value" 
            :number-of-months="2"
            class="[&_[data-selection-start]:hover]:!bg-primary [&_[data-selection-start]:hover]:!text-primary-foreground [&_[data-selection-end]:hover]:!bg-primary [&_[data-selection-end]:hover]:!text-primary-foreground"
            @update:start-value="(startDate) => value.start = startDate"
          />
          
          <!-- Time Selection -->
          <div v-if="includeTime" class="border-t pt-3 mt-3">
            <div class="grid grid-cols-2 gap-3">
              <!-- Start Time -->
              <div class="space-y-1.5">
                <Label class="text-xs font-medium text-muted-foreground">Start Time</Label>
                <Input 
                  type="time" 
                  v-model="startTime"
                  class="h-8 text-xs"
                />
              </div>
              
              <!-- End Time -->
              <div class="space-y-1.5">
                <Label class="text-xs font-medium text-muted-foreground">End Time</Label>
                <Input 
                  type="time" 
                  v-model="endTime"
                  class="h-8 text-xs"
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
import {
  CalendarDate,
  CalendarDateTime,
  DateFormatter,
  getLocalTimeZone,
  type DateValue,
  today,
  now,
  startOfWeek as rekaStartOfWeek,
  startOfMonth as rekaStartOfMonth,
  startOfYear as rekaStartOfYear,
  endOfWeek as rekaEndOfWeek,
  endOfMonth as rekaEndOfMonth,
  endOfYear as rekaEndOfYear,
} from '@internationalized/date'
import type { Ref } from 'vue'

interface DateRangeValue {
  from: Date | undefined
  to: Date | undefined
}

interface QuickPreset {
  label: string
  getValue: () => DateRange
}

const props = defineProps<{
  modelValue?: DateRangeValue
  includeTime?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: DateRangeValue]
}>()

const open = ref(false)

// Track active preset
const activePresetLabel = ref<string | null>(null)
const isSelectingPreset = ref(false)

// Time state - reactive refs
const startHour = ref('00')
const startMinute = ref('00')
const endHour = ref('23')
const endMinute = ref('59')

// Computed properties for v-model binding
const startTime = computed({
  get: () => `${startHour.value}:${startMinute.value}`,
  set: (value: string) => {
    const [h, m] = value.split(':')
    startHour.value = h || '00'
    startMinute.value = m || '00'
  }
})

const endTime = computed({
  get: () => `${endHour.value}:${endMinute.value}`,
  set: (value: string) => {
    const [h, m] = value.split(':')
    endHour.value = h || '23'
    endMinute.value = m || '59'
  }
})

const df = new DateFormatter('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
})

const dtf = new DateFormatter('en-US', {
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
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
      ? new CalendarDateTime(
          from.getFullYear(),
          from.getMonth() + 1,
          from.getDate(),
          from.getHours(),
          from.getMinutes()
        )
      : new CalendarDate(
          from.getFullYear(),
          from.getMonth() + 1,
          from.getDate()
        )
    
    const end = to 
      ? (props.includeTime 
          ? new CalendarDateTime(
              to.getFullYear(),
              to.getMonth() + 1,
              to.getDate(),
              to.getHours(),
              to.getMinutes()
            )
          : new CalendarDate(
              to.getFullYear(),
              to.getMonth() + 1,
              to.getDate()
            ))
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
        // If this is a new date selection (not just time change), set default times
        if (!props.modelValue?.from || baseDate.toDateString() !== props.modelValue.from.toDateString()) {
          startHour.value = '00'
          startMinute.value = '00'
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
        // If this is a new date selection (not just time change), set default times
        if (!props.modelValue?.to || baseDate.toDateString() !== props.modelValue.to.toDateString()) {
          endHour.value = '23'
          endMinute.value = '59'
        }
        to.setHours(parseInt(endHour.value), parseInt(endMinute.value))
      } else {
        to = baseDate
      }
    }
    
    emit('update:modelValue', { from, to })
  }
})

// Watch time changes and update the value
watch([startHour, startMinute, endHour, endMinute], () => {
  if (props.includeTime && value.value.start) {
    // Trigger an update with the new time values
    value.value = { ...value.value }
  }
})

const todayDate = today(getLocalTimeZone())
const nowDateTime = now(getLocalTimeZone())

const quickPresets: QuickPreset[] = [
  // Current period presets
  {
    label: 'Today',
    getValue: () => ({
      start: todayDate,
      end: todayDate,
    } as DateRange)
  },
  {
    label: 'This Week',
    getValue: () => ({
      start: rekaStartOfWeek(todayDate, 'en-US'),
      end: rekaEndOfWeek(todayDate, 'en-US'),
    } as DateRange)
  },
  {
    label: 'This Month',
    getValue: () => ({
      start: rekaStartOfMonth(todayDate),
      end: rekaEndOfMonth(todayDate),
    } as DateRange)
  },
  {
    label: 'This Year',
    getValue: () => ({
      start: rekaStartOfYear(todayDate),
      end: rekaEndOfYear(todayDate),
    } as DateRange)
  },
  // Hour-based presets
  {
    label: 'Last 1 Hour',
    getValue: () => {
      // Create CalendarDateTime from current time minus 1 hour
      const now = new Date()
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000)
      
      const start = new CalendarDateTime(
        oneHourAgo.getFullYear(),
        oneHourAgo.getMonth() + 1,
        oneHourAgo.getDate(),
        oneHourAgo.getHours(),
        oneHourAgo.getMinutes()
      )
      
      const end = new CalendarDateTime(
        now.getFullYear(),
        now.getMonth() + 1,
        now.getDate(),
        now.getHours(),
        now.getMinutes()
      )
      
      return {
        start,
        end,
      } as DateRange
    }
  },
  {
    label: 'Last 2 Hours',
    getValue: () => {
      const now = new Date()
      const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000)
      
      const start = new CalendarDateTime(
        twoHoursAgo.getFullYear(),
        twoHoursAgo.getMonth() + 1,
        twoHoursAgo.getDate(),
        twoHoursAgo.getHours(),
        twoHoursAgo.getMinutes()
      )
      
      const end = new CalendarDateTime(
        now.getFullYear(),
        now.getMonth() + 1,
        now.getDate(),
        now.getHours(),
        now.getMinutes()
      )
      
      return {
        start,
        end,
      } as DateRange
    }
  },
  // Day-based presets
  {
    label: 'Last 24 Hours',
    getValue: () => {
      const end = nowDateTime
      const start = nowDateTime.subtract({ days: 1 })
      return {
        start,
        end,
      } as DateRange
    }
  },
  {
    label: 'Last 2 Days',
    getValue: () => {
      const end = todayDate
      const start = todayDate.subtract({ days: 2 })
      return {
        start,
        end,
      } as DateRange
    }
  },
  {
    label: 'Last 7 Days',
    getValue: () => {
      const end = todayDate
      const start = todayDate.subtract({ days: 7 })
      return {
        start,
        end,
      } as DateRange
    }
  },
  // Week/Month/Year presets
  {
    label: 'Last 30 Days',
    getValue: () => {
      const end = todayDate
      const start = todayDate.subtract({ days: 30 })
      return {
        start,
        end,
      } as DateRange
    }
  },
  {
    label: 'Last 3 Months',
    getValue: () => {
      const end = todayDate
      const start = todayDate.subtract({ months: 3 })
      return {
        start,
        end,
      } as DateRange
    }
  },
  {
    label: 'Last 6 Months',
    getValue: () => {
      const end = todayDate
      const start = todayDate.subtract({ months: 6 })
      return {
        start,
        end,
      } as DateRange
    }
  },
  {
    label: 'Last 1 Year',
    getValue: () => {
      const end = todayDate
      const start = todayDate.subtract({ years: 1 })
      return {
        start,
        end,
      } as DateRange
    }
  }
]

function selectPreset(preset: QuickPreset) {
  const dateRange = preset.getValue()
  
  // Set flag to prevent watcher from clearing the preset
  isSelectingPreset.value = true
  
  // Track the active preset
  activePresetLabel.value = preset.label
  
  // For presets, set appropriate times
  if (props.includeTime && dateRange.start && dateRange.end) {
    const label = preset.label.toLowerCase()
    
    // For time-based presets (hours), preserve the actual times
    if (label.includes('hour')) {
      // Extract time from the CalendarDateTime
      const startDate = dateRange.start.toDate(getLocalTimeZone())
      const endDate = dateRange.end.toDate(getLocalTimeZone())
      
      startHour.value = String(startDate.getHours()).padStart(2, '0')
      startMinute.value = String(startDate.getMinutes()).padStart(2, '0')
      endHour.value = String(endDate.getHours()).padStart(2, '0')
      endMinute.value = String(endDate.getMinutes()).padStart(2, '0')
    } else if (label.includes('today') || label.includes('week') || label.includes('month') || label.includes('year')) {
      // For full day presets, use 00:00 - 23:59
      startHour.value = '00'
      startMinute.value = '00'
      endHour.value = '23'
      endMinute.value = '59'
    }
  }
  
  value.value = dateRange
  
  // Reset flag after a tick to allow the value to update
  nextTick(() => {
    isSelectingPreset.value = false
  })
  
  open.value = false
}

// Clear active preset when user manually changes the calendar
watch(value, (newValue, oldValue) => {
  // Skip if we're selecting a preset
  if (isSelectingPreset.value) return
  
  // Only clear if this wasn't triggered by selectPreset
  if (activePresetLabel.value && oldValue?.start && newValue?.start) {
    const oldStart = oldValue.start.toDate(getLocalTimeZone())
    const newStart = newValue.start.toDate(getLocalTimeZone())
    if (oldStart.getTime() !== newStart.getTime()) {
      activePresetLabel.value = null
    }
  }
})

// Check if current value matches any preset on mount
onMounted(() => {
  if (props.modelValue?.from && props.modelValue?.to) {
    checkForMatchingPreset()
  }
})

// Check if the current date range matches any preset
function checkForMatchingPreset() {
  if (!props.modelValue?.from || !props.modelValue?.to) {
    activePresetLabel.value = null
    return
  }
  
  const from = props.modelValue.from.getTime()
  const to = props.modelValue.to.getTime()
  
  // Check each preset to see if it matches
  for (const preset of quickPresets) {
    const presetRange = preset.getValue()
    if (presetRange.start && presetRange.end) {
      const presetFrom = presetRange.start.toDate(getLocalTimeZone()).getTime()
      const presetTo = presetRange.end.toDate(getLocalTimeZone()).getTime()
      
      // Allow small time differences (within 1 minute) for time-based presets
      const timeDiff = Math.abs(from - presetFrom) + Math.abs(to - presetTo)
      if (timeDiff < 60000) { // 1 minute tolerance
        activePresetLabel.value = preset.label
        return
      }
    }
  }
  
  activePresetLabel.value = null
}
</script>