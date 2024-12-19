export interface Alert {
  alert_id: number
  message_id: string
  create_time: string
  detect_time: string
  classification_text: string
  severity: 'high' | 'medium' | 'low'
  source_ipv4: string
  target_ipv4: string
  analyzer: {
    id: string
    name: string
  }
}

interface AlertsResponse {
  total: number
  items: Alert[]
  page: number
  size: number
}

interface AlertsFilter {
  search: string
  severity: string[]
  timeRange: string
  page: number
  size: number
  sort_by?: 'detect_time' | 'create_time' | 'severity' | 'classification' | 'source_ip' | 'target_ip' | 'analyzer' | 'alert_id'
  sort_order?: 'asc' | 'desc'
}

export function useAlerts() {
  const filters = reactive<AlertsFilter>({
    search: '',
    severity: [],
    timeRange: '1 day',
    page: 1,
    size: 20,
  })

  const { data, pending, error, refresh } = useFetch<AlertsResponse>('/api/alerts', {
    query: computed(() => ({
      ...filters,
    })),
  })

  const alerts = computed(() => data.value?.items ?? [])
  const total = computed(() => data.value?.total ?? 0)
  const totalPages = computed(() => {
    if (!total.value) return 0
    return Math.ceil(total.value / filters.size)
  })

  const setFilter = <K extends keyof AlertsFilter>(key: K, value: AlertsFilter[K]) => {
    filters[key] = value
    if (key !== 'page') {
      filters.page = 1 // Reset page when filters change
    }
  }

  const clearFilters = () => {
    filters.search = ''
    filters.severity = []
    filters.timeRange = '1 day'
    filters.page = 1
    filters.size = 20
    filters.sort_by = undefined
    filters.sort_order = undefined
  }

  const setPage = (page: number) => {
    filters.page = page
  }

  const setPageSize = (size: number) => {
    filters.size = size
    filters.page = 1
  }

  const setSorting = (
    field?: 'detect_time' | 'create_time' | 'severity' | 'classification' | 'source_ip' | 'target_ip' | 'analyzer' | 'alert_id',
    order?: 'asc' | 'desc'
  ) => {
    filters.sort_by = field
    filters.sort_order = order
  }

  return {
    alerts,
    pending,
    error,
    filters: readonly(filters),
    total,
    totalPages,
    setFilter,
    clearFilters,
    refresh,
    setPage,
    setPageSize,
    setSorting
  }
} 