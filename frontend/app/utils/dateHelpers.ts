// Date helper utilities for consistent date handling across the application
import { useNow } from '@vueuse/core'
import { computed } from 'vue'

export interface DateRange {
  from: Date | undefined
  to: Date | undefined
}

/**
 * Get today's date range (00:00:00 to 23:59:59)
 * Static version for non-reactive contexts
 */
export function getTodayRange(): DateRange {
  const now = new Date()
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const endOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999)
  return { from: startOfDay, to: endOfDay }
}

/**
 * Get reactive today's date range using VueUse
 */
export function useReactiveTodayRange() {
  const now = useNow()
  
  return computed(() => {
    const current = now.value
    const startOfDay = new Date(current.getFullYear(), current.getMonth(), current.getDate())
    const endOfDay = new Date(current.getFullYear(), current.getMonth(), current.getDate(), 23, 59, 59, 999)
    return { from: startOfDay, to: endOfDay }
  })
}

/**
 * Check if a date range represents "today" (00:00 to 23:59)
 */
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

/**
 * Apply default date filters if none are specified
 * Defaults to "today" range
 */
export function applyDefaultDateFilters(filters: Record<string, string | number>): Record<string, string | number> {
  if (!filters.start_date && !filters.end_date) {
    const { from, to } = getTodayRange()
    return {
      ...filters,
      start_date: from!.toISOString(),
      end_date: to!.toISOString()
    }
  }
  return filters
}