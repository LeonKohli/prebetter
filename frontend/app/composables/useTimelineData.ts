import type { TimelineResponse, TimeFrame } from '~~/shared/types/timeline'
import { getPresetRange, isValidPresetId, isRelativePreset, type DatePresetId } from '@/utils/datePresets'

/**
 * Timeline data composable for the alerts chart.
 */
export function useTimelineData(urlState: ReturnType<typeof useNavigableUrlState>) {
  const { token: sseRefreshToken } = useSseRefreshToken()

  function getActivePresetId(): DatePresetId | undefined {
    const preset = urlState.filters.value.date_preset
    return typeof preset === 'string' && isValidPresetId(preset) ? preset : undefined
  }

  /** Single source of truth for date range */
  const dateRange = computed(() => {
    const filters = urlState.filters.value
    const presetId = getActivePresetId()

    if (presetId) {
      // For relative presets, depend on sseRefreshToken to recalculate with fresh dates when SSE arrives
      if (isRelativePreset(presetId)) {
        void sseRefreshToken.value
      }
      const range = getPresetRange(presetId)
      return { start: range.from, end: range.to }
    }
    if (filters.start_date && filters.end_date) {
      return { start: new Date(filters.start_date as string), end: new Date(filters.end_date as string) }
    }
    return { start: new Date(Date.now() - 24 * 60 * 60 * 1000), end: new Date() }
  })

  /** Time frame based on range duration */
  const timeFrame = computed<TimeFrame>(() => {
    const hours = (dateRange.value.end.getTime() - dateRange.value.start.getTime()) / (1000 * 60 * 60)
    if (hours <= 168) return 'hour'  // ≤7 days
    if (hours <= 2160) return 'day'  // ≤90 days
    return 'week'
  })

  const fetchKey = computed(() => `timeline-${btoa(JSON.stringify({
    filters: urlState.filters.value,
    sseToken: sseRefreshToken.value,
  }))}`)

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

  const { data, pending, error, refresh, status, execute } = useFetch<TimelineResponse>('/api/statistics/timeline', {
    key: fetchKey,
    query: fetchQuery,
    server: true,
    lazy: false,
    dedupe: 'defer',
    watch: false
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
    data, pending, error, status, refresh, execute,
    chartSeries, totalAlerts, timeFrame, dateRange,
    fetchKey, getActivePresetId,
  }
}
