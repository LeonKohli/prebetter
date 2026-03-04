import type { TimelineResponse, TimeFrame } from '~~/shared/types/timeline'
import { getPresetRange, isRelativePreset, getActivePresetId } from '@/utils/datePresets'

export function useTimelineData(urlState: ReturnType<typeof useNavigableUrlState>) {
  const { token: sseRefreshToken } = useSseRefreshToken()

  const dateRange = computed(() => {
    const presetId = getActivePresetId(urlState.filters.value)
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

  const fetchKey = computed(() => {
    const presetId = getActivePresetId(urlState.filters.value)
    const filters = urlState.filters.value
    const hasExplicitDates = !!(filters.start_date && filters.end_date) && !presetId
    const includeToken = !!presetId || !hasExplicitDates

    return `timeline-${btoa(JSON.stringify({
      filters,
      ...(includeToken && { t: sseRefreshToken.value }),
    }))}`
  })

  const fetchQuery = computed(() => {
    const query: Record<string, string | boolean> = {
      time_frame: timeFrame.value,
      start_date: dateRange.value.start.toISOString(),
      end_date: dateRange.value.end.toISOString(),
    }
    const { severity, classification_text, source_ipv4, target_ipv4, require_ips } = urlState.filters.value
    if (severity) query.severity = String(severity)
    if (classification_text) query.classification = String(classification_text)
    if (source_ipv4) query.source_ip = String(source_ipv4)
    if (target_ipv4) query.target_ip = String(target_ipv4)
    if (require_ips === 'false') query.require_ips = false
    return query
  })

  // server: false — Timeline.client.vue never renders on server,
  // so shipping this data in the SSR HTML payload is pure waste
  const { data, pending, error, refresh, status } = useFetch<TimelineResponse>('/api/statistics/timeline', {
    key: fetchKey,
    query: fetchQuery,
    server: false,
    lazy: false,
    dedupe: 'defer',
  })

  const chartSeries = computed(() => {
    if (!data.value?.data) return [{ name: 'Alerts', data: [] as { x: number; y: number }[] }]

    return [{
      name: 'Alerts',
      data: data.value.data
        .map(p => ({ x: new Date(p.timestamp).getTime(), y: p.total }))
        .filter(p => Number.isFinite(p.x))
    }]
  })

  const totalAlerts = computed(() =>
    data.value?.data?.reduce((sum, p) => sum + p.total, 0) ?? 0
  )

  return {
    data, pending, error, status, refresh,
    chartSeries, totalAlerts, timeFrame, dateRange,
    fetchKey,
  }
}
