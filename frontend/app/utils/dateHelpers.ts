import { useNow } from '@vueuse/core'

export interface DateRange {
  from: Date | undefined
  to: Date | undefined
}

export function getTodayRange(): DateRange {
  const now = new Date()
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const endOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999)
  return { from: startOfDay, to: endOfDay }
}

export function getLast24HoursRange(): DateRange {
  const now = new Date()
  const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  return { from: twentyFourHoursAgo, to: now }
}

// Reactive date range that updates at midnight
export function useReactiveTodayRange() {
  const now = useNow()
  
  return computed(() => {
    const current = now.value
    const startOfDay = new Date(current.getFullYear(), current.getMonth(), current.getDate())
    const endOfDay = new Date(current.getFullYear(), current.getMonth(), current.getDate(), 23, 59, 59, 999)
    return { from: startOfDay, to: endOfDay }
  })
}

export function isToday(from: Date, to: Date): boolean {
  const today = new Date()
  return from.getFullYear() === today.getFullYear() &&
         from.getMonth() === today.getMonth() &&
         from.getDate() === today.getDate() &&
         from.getHours() === 0 &&
         from.getMinutes() === 0 &&
         to.getHours() === 23 &&
         to.getMinutes() === 59
}

export function applyDefaultDateFilters(filters: Record<string, string | number>): Record<string, string | number> {
  if (!filters.date_preset && !filters.start_date && !filters.end_date) {
    const { from, to } = getLast24HoursRange()
    return {
      ...filters,
      start_date: from!.toISOString(),
      end_date: to!.toISOString()
    }
  }
  return filters
}
