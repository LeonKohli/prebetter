import {
  CalendarDate,
  CalendarDateTime,
  Time,
  fromDate,
  getLocalTimeZone,
  startOfWeek,
  endOfWeek,
  startOfMonth,
  endOfMonth,
  startOfYear,
  endOfYear,
  toCalendarDate,
  toCalendarDateTime
} from '@internationalized/date'

export type DatePresetId =
  | 'last-1-hour'
  | 'last-2-hours'
  | 'last-24-hours'
  | 'last-2-days'
  | 'last-7-days'
  | 'last-30-days'
  | 'last-3-months'
  | 'last-6-months'
  | 'last-year'
  | 'today'
  | 'this-week'
  | 'this-month'
  | 'this-year'

export interface DatePreset {
  id: DatePresetId
  label: string
  relative: boolean
  computeRange: (now?: Date) => { from: Date; to: Date }
}

const MS_IN_MINUTE = 60 * 1000
const MS_IN_HOUR = 60 * MS_IN_MINUTE
const LOCAL_TZ = getLocalTimeZone()
const END_OF_DAY_TIME = new Time(23, 59, 59, 999)
const DEFAULT_LOCALE = 'de-DE'

function getReferenceDate(now?: Date): { calendarDate: CalendarDate; calendarDateTime: CalendarDateTime } {
  const reference = fromDate(now ?? new Date(), LOCAL_TZ)
  return {
    calendarDate: toCalendarDate(reference),
    calendarDateTime: toCalendarDateTime(reference)
  }
}

function toJsDate(value: CalendarDate | CalendarDateTime): Date {
  return value.toDate(LOCAL_TZ)
}

const hourPreset = (hours: number, label: string, id: DatePresetId): DatePreset => ({
  id,
  label,
  relative: true,
  computeRange: (now = new Date()) => {
    const end = new Date(now)
    const start = new Date(now.getTime() - hours * MS_IN_HOUR)
    return { from: start, to: end }
  }
})

const dayWindowPreset = (days: number, label: string, id: DatePresetId): DatePreset => ({
  id,
  label,
  relative: true,
  computeRange: (now = new Date()) => {
    const { calendarDate } = getReferenceDate(now)
    const startCalendar = calendarDate.subtract({ days })
    const endCalendar = calendarDate
    return {
      from: toJsDate(toCalendarDateTime(startCalendar)),
      to: toJsDate(toCalendarDateTime(endCalendar, END_OF_DAY_TIME))
    }
  }
})

const monthWindowPreset = (months: number, label: string, id: DatePresetId): DatePreset => ({
  id,
  label,
  relative: true,
  computeRange: (now = new Date()) => {
    const { calendarDate } = getReferenceDate(now)
    const startCalendar = calendarDate.subtract({ months })
    return {
      from: toJsDate(toCalendarDateTime(startCalendar)),
      to: toJsDate(toCalendarDateTime(calendarDate, END_OF_DAY_TIME))
    }
  }
})

const yearWindowPreset = (years: number, label: string, id: DatePresetId): DatePreset => ({
  id,
  label,
  relative: true,
  computeRange: (now = new Date()) => {
    const { calendarDate } = getReferenceDate(now)
    const startCalendar = calendarDate.subtract({ years })
    return {
      from: toJsDate(toCalendarDateTime(startCalendar)),
      to: toJsDate(toCalendarDateTime(calendarDate, END_OF_DAY_TIME))
    }
  }
})

export const DATE_PRESETS: DatePreset[] = [
  hourPreset(1, 'Last Hour', 'last-1-hour'),
  hourPreset(2, 'Last 2 Hours', 'last-2-hours'),
  hourPreset(24, 'Last 24 Hours', 'last-24-hours'),
  dayWindowPreset(2, 'Last 2 Days', 'last-2-days'),
  dayWindowPreset(7, 'Last 7 Days', 'last-7-days'),
  dayWindowPreset(30, 'Last 30 Days', 'last-30-days'),
  monthWindowPreset(3, 'Last 3 Months', 'last-3-months'),
  monthWindowPreset(6, 'Last 6 Months', 'last-6-months'),
  yearWindowPreset(1, 'Last Year', 'last-year'),
  {
    id: 'today',
    label: 'Today',
    relative: false,
    computeRange: (now = new Date()) => {
      const { calendarDate } = getReferenceDate(now)
      return {
        from: toJsDate(toCalendarDateTime(calendarDate)),
        to: toJsDate(toCalendarDateTime(calendarDate, END_OF_DAY_TIME))
      }
    }
  },
  {
    id: 'this-week',
    label: 'This Week',
    relative: false,
    computeRange: (now = new Date()) => {
      const { calendarDate } = getReferenceDate(now)
      const start = startOfWeek(calendarDate, DEFAULT_LOCALE)
      const end = endOfWeek(calendarDate, DEFAULT_LOCALE)
      return {
        from: toJsDate(toCalendarDateTime(start)),
        to: toJsDate(toCalendarDateTime(end, END_OF_DAY_TIME))
      }
    }
  },
  {
    id: 'this-month',
    label: 'This Month',
    relative: false,
    computeRange: (now = new Date()) => {
      const { calendarDate } = getReferenceDate(now)
      const start = startOfMonth(calendarDate)
      const end = endOfMonth(calendarDate)
      return {
        from: toJsDate(toCalendarDateTime(start)),
        to: toJsDate(toCalendarDateTime(end, END_OF_DAY_TIME))
      }
    }
  },
  {
    id: 'this-year',
    label: 'This Year', 
    relative: false,
    computeRange: (now = new Date()) => {
      const { calendarDate } = getReferenceDate(now)
      const start = startOfYear(calendarDate)
      const end = endOfYear(calendarDate)
      return {
        from: toJsDate(toCalendarDateTime(start)),
        to: toJsDate(toCalendarDateTime(end, END_OF_DAY_TIME))
      }
    }
  }
]

const PRESET_MAP = new Map<DatePresetId, DatePreset>(DATE_PRESETS.map(preset => [preset.id, preset]))

export function isValidPresetId(id: string | undefined): id is DatePresetId {
  return !!id && PRESET_MAP.has(id as DatePresetId)
}

export function getPresetRange(id: DatePresetId, now = new Date()): { from: Date; to: Date } {
  // TypeScript guarantees id is a valid DatePresetId, so preset always exists
  return PRESET_MAP.get(id)!.computeRange(now)
}

export function isRelativePreset(id: DatePresetId | null | undefined): boolean {
  if (!id) return false
  const preset = PRESET_MAP.get(id)
  return preset?.relative ?? false
}

export function getPresetLabel(id: DatePresetId): string {
  return PRESET_MAP.get(id)?.label ?? id
}
