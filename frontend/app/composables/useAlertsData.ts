/**
 * Alerts data fetching composable.
 * Minimal wrapper around useFetch with URL state sync.
 *
 * SSE refresh behavior:
 * - All presets: Token in fetchKey → triggers data refresh on SSE
 * - Relative presets (last-24h): Token in fetchQuery → dates recalculate with fresh Date()
 * - Non-relative presets (today): Dates stay fixed, but data still refreshes
 * - Explicit user dates: No SSE refresh (user-selected range)
 */
import { getPresetRange, isRelativePreset, getActivePresetId, type DatePresetId } from '@/utils/datePresets'

export function useAlertsData(urlState: ReturnType<typeof useNavigableUrlState>) {
  const { sortFieldMap, filterFieldMap } = useAlertTableColumns()
  const { token: sseRefreshToken } = useSseRefreshToken()

  const isGrouped = computed(() => urlState.view.value === 'grouped')
  const fetchUrl = computed(() => isGrouped.value ? '/api/alerts/groups' : '/api/alerts')

  const fetchKey = computed(() => {
    const presetId = getActivePresetId(urlState.filters.value)
    const filters = urlState.filters.value
    const hasExplicitDates = !!(filters.start_date && filters.end_date) && !presetId
    // Include token for SSE refresh: any preset OR default fallback (but not explicit user dates)
    const includeToken = !!presetId || !hasExplicitDates

    return `alerts-${btoa(JSON.stringify({
      view: urlState.view.value,
      page: urlState.page.value,
      pageSize: urlState.pageSize.value,
      sortBy: urlState.sortBy.value,
      sortOrder: urlState.sortOrder.value,
      filters: filters,
      ...(includeToken && { t: sseRefreshToken.value }),
    }))}`
  })

  const fetchQuery = computed(() => {
    const activePreset = getActivePresetId(urlState.filters.value)
    const sortBy = urlState.sortBy.value
    const mappedSort = sortBy in sortFieldMap ? sortFieldMap[sortBy as keyof typeof sortFieldMap] : sortBy
    const urlFilters = urlState.filters.value
    const hasExplicitDates = !!(urlFilters.start_date && urlFilters.end_date)

    // Build filters without date_preset
    const filters: Record<string, string | number> = {}
    for (const [k, v] of Object.entries(urlFilters)) {
      if (k === 'date_preset') continue
      filters[k in filterFieldMap ? filterFieldMap[k as keyof typeof filterFieldMap] : k] = v
    }

    // Convert preset to dates (with SSE token dependency for sliding windows)
    if (activePreset) {
      if (isRelativePreset(activePreset)) {
        void sseRefreshToken.value
      }
      const range = getPresetRange(activePreset)
      filters.start_date = range.from.toISOString()
      filters.end_date = range.to.toISOString()
    } else if (!hasExplicitDates) {
      // Default fallback - sliding 24h window
      void sseRefreshToken.value
      const range = getPresetRange('last-24-hours')
      filters.start_date = range.from.toISOString()
      filters.end_date = range.to.toISOString()
    }

    return {
      page: urlState.page.value,
      size: urlState.pageSize.value,
      sort_by: mappedSort || 'detect_time',
      sort_order: urlState.sortOrder.value,
      ...filters
    }
  })

  // Explicit generic required - catch-all proxy returns untyped data
  // Nuxt natively watches reactive query - no manual watchers needed
  const { data, pending, error, refresh, status } = useFetch<GroupedAlertResponse | AlertListResponse>(fetchUrl, {
    key: fetchKey,
    query: fetchQuery,
    server: true,
    lazy: false,
    dedupe: 'defer',
    // Strip analyzer/analyzer_host from grouped alert details before SSR serialization.
    // These arrays are never rendered in the table — only classification, count, detected_at are used.
    // Saves ~30-50% of grouped response payload from the SSR HTML.
    transform: (response) => {
      if ('groups' in response) {
        return {
          ...response,
          groups: response.groups.map(g => ({
            ...g,
            alerts: g.alerts.map(({ classification, count, detected_at }) => ({
              classification, count, detected_at,
            })),
          })),
        } as GroupedAlertResponse
      }
      return response
    },
  })

  // Type guard - zero runtime cost, just checks property existence
  const isGroupedResponse = (d: unknown): d is GroupedAlertResponse =>
    d !== null && typeof d === 'object' && 'groups' in d

  // Derived state - returns empty during view transition to prevent column/data mismatch
  const displayData = computed(() => {
    if (!data.value) return []
    if (isGroupedResponse(data.value)) {
      if (!isGrouped.value) return [] // Grouped data but ungrouped view - transitioning
      return data.value.groups
    }
    if (isGrouped.value) return [] // Ungrouped data but grouped view - transitioning
    return data.value.items ?? []
  })

  const paginationInfo = computed(() => {
    if (!data.value) return { total: 0, pages: 0, page: 1, size: 100 }
    return isGroupedResponse(data.value)
      ? data.value.pagination
      : (data.value as AlertListResponse).pagination
  })

  const tableTotals = computed(() => {
    if (!data.value) return { rows: 0, alerts: 0, total: 0 }
    if (isGroupedResponse(data.value)) {
      return {
        rows: data.value.groups.length,
        alerts: data.value.total_alerts,
        total: data.value.pagination.total
      }
    }
    const items = (data.value as AlertListResponse).items ?? []
    return { rows: items.length, alerts: items.length, total: paginationInfo.value.total }
  })

  return {
    data, pending, error, status, refresh,
    isGrouped, displayData, paginationInfo, tableTotals, fetchKey,
  }
}
