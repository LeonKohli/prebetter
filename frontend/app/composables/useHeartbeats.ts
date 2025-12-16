const WELL_KNOWN_STATUSES = ['active', 'inactive', 'offline', 'unknown'] as const

type WellKnownStatus = (typeof WELL_KNOWN_STATUSES)[number]

export function useHeartbeatStatus(options: {
  days?: number
  autoRefreshMs?: number
  immediate?: boolean
} = {}) {
  const days = ref(options.days ?? 1)
  const lastUpdated = ref<Date | null>(null)
  const autoRefreshInterval = ref(options.autoRefreshMs ?? 30_000)
  const autoRefreshEnabled = ref(true)

  const fetchKey = computed(() => `heartbeat-status-${days.value}`)
  const fetchQuery = computed(() => ({ days: days.value }))

  const fetchResult = useFetch<HeartbeatTreeResponse>('/api/heartbeats/status', {
    key: fetchKey,
    query: fetchQuery,
    watch: [days],
    immediate: options.immediate ?? true,
    lazy: !(options.immediate ?? true),
    server: true,
  })

  const { data, pending, error, refresh, status } = fetchResult

  const nodes = computed<HeartbeatNode[]>(() => data.value?.nodes ?? [])
  const totalNodes = computed(() => data.value?.total_nodes ?? 0)
  const totalAgents = computed(() => data.value?.total_agents ?? 0)

  const statusSummary = computed<HeartbeatStatusSummary>(() => {
    const summary = data.value?.status_summary ?? {}
    const normalised: HeartbeatStatusSummary = {}

    for (const key of WELL_KNOWN_STATUSES) {
      normalised[key] = summary[key] ?? 0
    }

    for (const [key, value] of Object.entries(summary)) {
      if (normalised[key] === undefined) {
        normalised[key] = value
      }
    }

    return normalised
  })

  const statusSummaryList = computed(() => {
    const base = WELL_KNOWN_STATUSES.map((statusKey) => ({
      status: statusKey as string,
      count: statusSummary.value[statusKey] ?? 0,
    }))

    const extras = Object.entries(statusSummary.value)
      .filter(([key]) => !WELL_KNOWN_STATUSES.includes(key as WellKnownStatus))
      .map(([statusKey, count]) => ({ status: statusKey, count }))

    return [...base, ...extras]
  })

  watch(
    data,
    (value) => {
      if (value) {
        lastUpdated.value = new Date()
      }
    },
    { immediate: true }
  )

  // Only set up interval-based refresh if autoRefreshMs > 0
  // When SSE is used, pass autoRefreshMs: 0 to disable polling
  const { pause: pauseAutoRefresh, resume: resumeAutoRefresh } = useIntervalFn(
    () => {
      refresh()
    },
    autoRefreshInterval,
    { immediate: false }
  )

  watch(
    autoRefreshEnabled,
    (enabled) => {
      // Don't start polling if interval is 0 (SSE mode)
      if (enabled && autoRefreshInterval.value > 0) {
        resumeAutoRefresh()
      } else {
        pauseAutoRefresh()
      }
    },
    { immediate: true }
  )

  onBeforeUnmount(() => {
    pauseAutoRefresh()
  })

  return {
    data,
    nodes,
    totalNodes,
    totalAgents,
    statusSummary,
    statusSummaryList,
    pending,
    error,
    refresh,
    status,
    days,
    setDays(value: number) {
      days.value = value
    },
    lastUpdated,
    autoRefreshEnabled,
    autoRefreshInterval,
    setAutoRefreshInterval(value: number) {
      autoRefreshInterval.value = value
    },
  }
}

export function useHeartbeatTimeline(options: { hours?: number; pageSize?: number } = {}) {
  const hours = ref(options.hours ?? 24)
  const page = ref(1)
  const pageSize = ref(options.pageSize ?? 100)

  const fetchKey = computed(() => `heartbeat-timeline-${hours.value}-${page.value}-${pageSize.value}`)
  const fetchQuery = computed(() => ({
    hours: hours.value,
    page: page.value,
    size: pageSize.value,
  }))

  const fetchResult = useFetch<PaginatedHeartbeatTimelineResponse>('/api/heartbeats/timeline', {
    key: fetchKey,
    query: fetchQuery,
    watch: [hours, page, pageSize],
    immediate: true,
    lazy: false,
    server: true,
  })

  const { data, pending, error, refresh, status } = fetchResult

  const items = computed<HeartbeatTimelineItem[]>(() => data.value?.items ?? [])
  const pagination = computed(() => data.value?.pagination ?? {
    total: 0,
    page: page.value,
    size: pageSize.value,
    pages: 0,
  })

  const setPage = (value: number) => {
    page.value = Math.max(1, value)
  }

  const setHours = (value: number) => {
    hours.value = value
    page.value = 1
  }

  return {
    data,
    items,
    pending,
    error,
    refresh,
    status,
    pagination,
    hours,
    page,
    pageSize,
    setPage,
    setHours,
    setPageSize(value: number) {
      pageSize.value = Math.max(1, value)
    },
  }
}

export function formatRelativeFromSeconds(seconds: number | null | undefined) {
  if (seconds == null || seconds < 0) {
    return 'No heartbeat received yet'
  }

  if (seconds < 60) {
    return `${seconds} second${seconds === 1 ? '' : 's'} ago`
  }

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) {
    return `${minutes} minute${minutes === 1 ? '' : 's'} ago`
  }

  const hours = Math.floor(minutes / 60)
  if (hours < 24) {
    return `${hours} hour${hours === 1 ? '' : 's'} ago`
  }

  const days = Math.floor(hours / 24)
  if (days < 30) {
    return `${days} day${days === 1 ? '' : 's'} ago`
  }

  const months = Math.floor(days / 30)
  if (months < 12) {
    return `${months} month${months === 1 ? '' : 's'} ago`
  }

  const years = Math.floor(months / 12)
  return `${years} year${years === 1 ? '' : 's'} ago`
}
