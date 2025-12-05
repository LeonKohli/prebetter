interface UseAlertStreamOptions {
  /** Auto-connect on mount (default: true) */
  immediate?: boolean
  /** Initial last known alert ID */
  lastId?: number | null
  /** Callback when new alerts arrive (debounced) */
  onNewAlerts?: () => void
  /** Debounce delay for onNewAlerts callback (default: 1000ms) */
  debounceMs?: number
}

/**
 * Composable for receiving real-time alert updates via Server-Sent Events.
 *
 * @example
 * ```vue
 * <script setup>
 * const { latestAlert, isConnected, newAlertCount, alerts } = useAlertStream()
 *
 * // React to new alerts
 * watch(latestAlert, (alert) => {
 *   if (alert) toast.info(`New alert: ${alert.classification_text}`)
 * })
 * </script>
 * ```
 */
export function useAlertStream(options: UseAlertStreamOptions = {}) {
  const {
    immediate = true,
    lastId: initialLastId = null,
    onNewAlerts,
    debounceMs = 1000
  } = options

  // Debounced callback for new alerts - batches rapid updates
  const debouncedOnNewAlerts = onNewAlerts
    ? useDebounceFn(onNewAlerts, debounceMs)
    : undefined

  // Track the last known alert ID for reconnection
  const lastKnownId = ref<number | null>(initialLastId)

  const url = '/api/alerts-stream'

  // VueUse's useEventSource handles reconnection and Last-Event-ID header natively
  // withCredentials: true is REQUIRED to send session cookies to the Nuxt server proxy
  const { status, data, error, close, open } = useEventSource(url, ['alert'], {
    immediate,
    withCredentials: true,
    autoReconnect: {
      retries: -1,
      delay: 2000,
      onFailed() {
        console.error('[AlertStream] Failed to reconnect to alert stream')
      },
    },
  })

  // Store received alerts (newest first, limited buffer)
  const alerts = ref<AlertListItem[]>([])
  const maxBufferSize = 100

  // Parse incoming alert data
  const latestAlert = computed<AlertListItem | null>(() => {
    if (!data.value) return null
    try {
      return JSON.parse(data.value) as AlertListItem
    } catch {
      return null
    }
  })

  // When we receive a new alert, add it to the buffer and notify
  watch(latestAlert, (alert) => {
    if (!alert) return

    // Update last known ID for reconnection
    const alertId = parseInt(alert.id, 10)
    if (!Number.isNaN(alertId)) {
      lastKnownId.value = alertId
    }

    // Prepend to alerts buffer (newest first)
    alerts.value = [alert, ...alerts.value].slice(0, maxBufferSize)

    // Notify callback (debounced) - this triggers table refresh
    debouncedOnNewAlerts?.()
  })

  // Count of new alerts since stream started
  const newAlertCount = computed(() => alerts.value.length)

  // Connection state helpers
  const isConnected = computed(() => status.value === 'OPEN')
  const isConnecting = computed(() => status.value === 'CONNECTING')

  // Clear the alerts buffer
  function clearAlerts() {
    alerts.value = []
  }

  // Set last known ID (useful when loading initial data)
  function setLastKnownId(id: number | null) {
    lastKnownId.value = id
  }

  // Manually force a reconnect (Last-Event-ID header handled by browser)
  function reconnect() {
    open()
  }

  return {
    // Connection state
    status,
    isConnected,
    isConnecting,
    error,

    // Alert data
    latestAlert,
    alerts,
    newAlertCount,

    // Actions
    close,
    open,
    reconnect,
    clearAlerts,
    setLastKnownId,
  }
}
