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
                  <Label class="text-xs font-medium text-muted-foreground">
                    End Time
                    <span v-if="currentPresetId && isRelativePreset(currentPresetId)" class="ml-1 text-[10px] opacity-60">(now)</span>
                  </Label>
                  <span class="text-xs text-muted-foreground">{{ endTime }}</span>
                </div>
                <Input
                  type="time"
                  v-model="endTime"
                  class="h-8 text-xs"
                  step="60"
                  lang="de-DE"
                  :disabled="currentPresetId && isRelativePreset(currentPresetId)"
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
import { useNow } from '@vueuse/core'
import type { DateRange } from 'reka-ui'
import {
  CalendarDate,
  CalendarDateTime,
  DateFormatter,
  getLocalTimeZone,
} from '@internationalized/date'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { RangeCalendar } from '@/components/ui/range-calendar'
import { DATE_PRESETS, getPresetRange, getPresetLabel, isRelativePreset, isValidPresetId, type DatePreset, type DatePresetId } from '@/utils/datePresets'


interface DateRangeValue {
  from: Date | undefined
  to: Date | undefined
  // Track which preset was selected (optional, for stability)
  presetId?: DatePresetId
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
const pickerValue: Ref<DateRange> = ref({ start: undefined, end: undefined })

// Stable preset tracking: rely on an explicit presetId instead of
// reverse-matching against a moving "now()" window.
const selectedPresetId = ref<DatePresetId | null>(null)

// Sync down from v-model if parent provides presetId (do not clear when undefined)
watch(
  () => props.modelValue?.presetId,
  (id) => {
    if (isValidPresetId(id)) selectedPresetId.value = id
  },
  { immediate: true }
)

const currentPresetId = computed<DatePresetId | null>(() => {
  const modelPreset = props.modelValue?.presetId
  if (isValidPresetId(modelPreset)) return modelPreset
  return selectedPresetId.value
})
// Header label: preset label if present, otherwise 'Custom' when user selected a manual range
const displayLabel = computed(() => currentPresetId.value ? getPresetLabel(currentPresetId.value) : (pickerValue.value?.start ? 'Custom' : null))

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
  get: () => {
    const presetId = currentPresetId.value
    if (presetId && isRelativePreset(presetId)) {
      // For relative presets, show current time (updates automatically)
      currentTime.value // Track dependency
      const now = new Date()
      const h = String(now.getHours()).padStart(2, '0')
      const m = String(now.getMinutes()).padStart(2, '0')
      return `${h}:${m}`
    }
    return `${endHour.value}:${endMinute.value}`
  },
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

  // For relative presets, always show current time as end time
  // This ensures the display updates even when the actual end time is computed server-side
  const presetId = currentPresetId.value
  let endDate = pickerValue.value.end.toDate(getLocalTimeZone())

  if (presetId && isRelativePreset(presetId)) {
    // Use current time for display (triggers reactivity via currentTime)
    currentTime.value // Track dependency
    endDate = new Date() // Always show "now" for relative presets
  }

  const endStr = formatter.format(endDate)
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

// Reactive current time using VueUse
const currentTime = useNow()

// Helper function to convert Date to CalendarDateTime
function dateToCalendarDateTime(date: Date): CalendarDateTime {
  return new CalendarDateTime(
    date.getFullYear(),
    date.getMonth() + 1,
    date.getDate(),
    date.getHours(),
    date.getMinutes(),
    date.getSeconds(),
    date.getMilliseconds()
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

const quickPresets = DATE_PRESETS

// Guard to distinguish preset-driven updates from manual ones
const isSettingFromPreset = ref(false)

function selectPreset(preset: DatePreset) {
  const { from, to } = preset.computeRange(currentTime.value)
  selectedPresetId.value = preset.id
  isSettingFromPreset.value = true

  if (props.includeTime) {
    startHour.value = String(from.getHours()).padStart(2, '0')
    startMinute.value = String(from.getMinutes()).padStart(2, '0')
    endHour.value = String(to.getHours()).padStart(2, '0')
    endMinute.value = String(to.getMinutes()).padStart(2, '0')
  }

  nextTick(() => {
    pickerValue.value = {
      start: dateToCalendarDateTime(from),
      end: dateToCalendarDateTime(to)
    }
    emitFromPicker(false)
    open.value = false
    nextTick(() => { isSettingFromPreset.value = false })
  })
}

// No complex watchers needed - the computed property handles everything!
</script>
