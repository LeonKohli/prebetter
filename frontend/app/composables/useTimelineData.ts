import type { TimelineResponse, TimeFrame } from '~~/shared/types/timeline'
import { getPresetRange, isValidPresetId, isRelativePreset, type DatePresetId } from '@/utils/datePresets'

/**
 * Timeline data composable for the alerts chart.
 *
 * SSE refresh behavior:
 * - All presets: Token in fetchKey → triggers data refresh on SSE
 * - Relative presets (last-24h): Token in dateRange → dates recalculate with fresh Date()
 * - Non-relative presets (today): Dates stay fixed, but data still refreshes
 * - Explicit user dates: No SSE refresh (user-selected range)
 */
export function useTimelineData(urlState: ReturnType<typeof useNavigableUrlState>) {
  const { token: sseRefreshToken } = useSseRefreshToken()

  function getActivePresetId(): DatePresetId | undefined {
    const preset = urlState.filters.value.date_preset
    return typeof preset === 'string' && isValidPresetId(preset) ? preset : undefined
  }

  /**
   * Date range computed with SSE refresh support.
   * Uses `void sseRefreshToken.value` to create reactive dependency for sliding windows,
   * forcing recalculation with fresh Date() when SSE arrives.
   */
  const dateRange = computed(() => {
    const presetId = getActivePresetId()
    const filters = urlState.filters.value

    if (presetId) {
      if (isRelativePreset(presetId)) {
        void sseRefreshToken.value
      }
      const range = getPresetRange(presetId)
      return { start: range.from, end: range.to }
    }

    if (filters.start_date && filters.end_date) {
      return { start: new Date(filters.start_date as string), end: new Date(filters.end_date as string) }
    }

    // Default: sliding 24h window - needs token dependency for SSE refresh
    void sseRefreshToken.value
    return { start: new Date(Date.now() - 24 * 60 * 60 * 1000), end: new Date() }
  })

  const timeFrame = computed<TimeFrame>(() => {
    const hours = (dateRange.value.end.getTime() - dateRange.value.start.getTime()) / (1000 * 60 * 60)
    if (hours <= 168) return 'hour'
    if (hours <= 2160) return 'day'
    return 'week'
  })

  /**
   * Fetch key includes token for live updates.
   * Token is included for ANY preset (triggers SSE refresh) but NOT for explicit user-selected dates.
   * When key changes, Nuxt creates new fetch with fresh query evaluation.
   */
  const fetchKey = computed(() => {
    const presetId = getActivePresetId()
    const filters = urlState.filters.value
    const hasExplicitDates = !!(filters.start_date && filters.end_date) && !presetId
    // Include token for SSE refresh: any preset OR default fallback (but not explicit user dates)
    const includeToken = !!presetId || !hasExplicitDates

    return `timeline-${btoa(JSON.stringify({
      filters,
      ...(includeToken && { t: sseRefreshToken.value }),
    }))}`
  })

  const fetchQuery = computed(() => {
    const query: Record<string, string> = {
      time_frame: timeFrame.value,
      start_date: dateRange.value.start.toISOString(),
      end_date: dateRange.value.end.toISOString(),
    }
    const { severity, classification_text } = urlState.filters.value
    if (severity) query.severity = String(severity)
    if (classification_text) query.classification = String(classification_text)
    return query
  })

  const { data, pending, error, refresh, status } = useFetch<TimelineResponse>('/api/statistics/timeline', {
    key: fetchKey,
    query: fetchQuery,
    server: true,
    lazy: false,
    dedupe: 'defer',
  })

  const chartSeries = computed(() => {
    if (!data.value?.data) return [{ name: 'Alerts', data: [] as { x: number; y: number }[] }]
    return [{
      name: 'Alerts',
      data: data.value.data.map(p => ({ x: new Date(p.timestamp).getTime(), y: p.total }))
    }]
  })

  const totalAlerts = computed(() =>
    data.value?.data?.reduce((sum, p) => sum + p.total, 0) ?? 0
  )

  return {
    data, pending, error, status, refresh,
    chartSeries, totalAlerts, timeFrame, dateRange,
    fetchKey, getActivePresetId,
  }
}
