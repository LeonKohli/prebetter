/**
 * Alerts data fetching composable.
 * Minimal wrapper around useFetch with URL state sync.
 */
export function useAlertsData(urlState: ReturnType<typeof useNavigableUrlState>) {
  const { sortFieldMap, filterFieldMap } = useAlertTableColumns()

  const relativeRefreshToken = ref(0)
  const isGrouped = computed(() => urlState.view.value === 'grouped')
  const fetchUrl = computed(() => isGrouped.value ? '/api/alerts/groups' : '/api/alerts')

  function getActivePresetId(): DatePresetId | undefined {
    const preset = urlState.filters.value.date_preset
    return typeof preset === 'string' && isValidPresetId(preset) ? preset : undefined
  }

  const fetchKey = computed(() => {
    const presetId = getActivePresetId()
    const relativeToken = presetId && isRelativePreset(presetId) ? relativeRefreshToken.value : 0
    return `alerts-${btoa(JSON.stringify({
      view: urlState.view.value,
      page: urlState.page.value,
      pageSize: urlState.pageSize.value,
      sortBy: urlState.sortBy.value,
      sortOrder: urlState.sortOrder.value,
      filters: urlState.filters.value,
      relativeToken,
    }))}`
  })

  const fetchQuery = computed(() => {
    const activePreset = getActivePresetId()
    const sortBy = urlState.sortBy.value
    const mappedSort = sortBy in sortFieldMap ? sortFieldMap[sortBy as keyof typeof sortFieldMap] : sortBy

    // Build filters without date_preset
    const filters: Record<string, string | number> = {}
    for (const [k, v] of Object.entries(urlState.filters.value)) {
      if (k === 'date_preset') continue
      filters[k in filterFieldMap ? filterFieldMap[k as keyof typeof filterFieldMap] : k] = v
    }

    // Convert preset to dates
    if (activePreset) {
      filters.start_date = getPresetRange(activePreset).from.toISOString()
      if (!isRelativePreset(activePreset)) {
        filters.end_date = getPresetRange(activePreset).to.toISOString()
      }
    } else if (!filters.start_date) {
      filters.start_date = getPresetRange('last-24-hours').from.toISOString()
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
  const { data, pending, error, refresh, status, execute } = useFetch<GroupedAlertResponse | AlertListResponse>(fetchUrl, {
    key: fetchKey,
    query: fetchQuery,
    server: true,
    lazy: false,
    dedupe: 'defer',
    watch: false
  })

  // Type guard - zero runtime cost, just checks property existence
  const isGroupedResponse = (d: unknown): d is GroupedAlertResponse =>
    d !== null && typeof d === 'object' && 'groups' in d

  // Derived state - use type guard inline, no transform/remapping
  const displayData = computed(() => {
    if (!data.value) return []
    return isGroupedResponse(data.value)
      ? data.value.groups.map((g, i) => ({ ...g, groupIndex: i }))
      : (data.value as AlertListResponse).items ?? []
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

  function triggerRelativeRefresh() {
    const presetId = getActivePresetId()
    if (presetId && isRelativePreset(presetId)) {
      relativeRefreshToken.value = Date.now()
    }
  }

  return {
    data, pending, error, status, refresh, execute,
    isGrouped, displayData, paginationInfo, tableTotals, fetchKey,
    relativeRefreshToken, getActivePresetId, triggerRelativeRefresh,
  }
}
