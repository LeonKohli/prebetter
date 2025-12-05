interface HeartbeatUpdateEvent {
  latest_timestamp: string
  new_count: number
}

interface UseHeartbeatStreamOptions {
  /** Auto-connect on mount (default: false to avoid 401 race on page load) */
  immediate?: boolean
  /** Callback when new heartbeats arrive (debounced) */
  onNewHeartbeats?: () => void
  /** Debounce delay for onNewHeartbeats callback (default: 1000ms) */
  debounceMs?: number
}

/**
 * Composable for receiving real-time heartbeat updates via Server-Sent Events.
 *
 * Unlike the alerts stream which sends individual alert records, the heartbeat
 * stream sends update notifications (latest timestamp + count of new heartbeats).
 * This is more efficient since heartbeats arrive frequently and we only need
 * to trigger a refresh, not process individual records.
 *
 * @example
 * ```vue
 * <script setup>
 * const { isConnected } = useHeartbeatStream({
 *   onNewHeartbeats: () => refreshHeartbeats()
 * })
 * </script>
 * ```
 */
export function useHeartbeatStream(options: UseHeartbeatStreamOptions = {}) {
  const {
    immediate = false,
    onNewHeartbeats,
    debounceMs = 1000
  } = options

  // Debounced callback for new heartbeats - batches rapid updates
  const debouncedOnNewHeartbeats = onNewHeartbeats
    ? useDebounceFn(onNewHeartbeats, debounceMs)
    : undefined

  const url = '/api/heartbeats-stream'

  // VueUse's useEventSource handles reconnection automatically
  // withCredentials: true is REQUIRED to send session cookies to the Nuxt server proxy
  const { status, data, error, close, open } = useEventSource(url, ['heartbeat_update'], {
    immediate,
    withCredentials: true,
    autoReconnect: {
      retries: 3,
      delay: 2000,
      onFailed() {
        console.error('[HeartbeatStream] Failed to connect after 3 retries')
      },
    },
  })

  // Parse incoming heartbeat update data
  const latestUpdate = computed<HeartbeatUpdateEvent | null>(() => {
    if (!data.value) return null
    try {
      return JSON.parse(data.value) as HeartbeatUpdateEvent
    } catch {
      return null
    }
  })

  // When we receive a new update, notify callback
  watch(latestUpdate, (update) => {
    if (!update) return
    debouncedOnNewHeartbeats?.()
  })

  // Connection state helpers
  const isConnected = computed(() => status.value === 'OPEN')
  const isConnecting = computed(() => status.value === 'CONNECTING')

  return {
    // Connection state
    status,
    isConnected,
    isConnecting,
    error,

    // Update data
    latestUpdate,

    // Actions
    close,
    open,
  }
}
