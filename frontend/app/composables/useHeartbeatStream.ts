interface HeartbeatUpdateEvent {
  latest_timestamp: string
  new_count: number
}

interface UseHeartbeatStreamOptions {
  /** Auto-connect on mount (default: true) */
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
    immediate = true,
    onNewHeartbeats,
    debounceMs = 1000
  } = options

  // Debounced callback for new heartbeats - batches rapid updates
  const debouncedOnNewHeartbeats = onNewHeartbeats
    ? useDebounceFn(onNewHeartbeats, debounceMs)
    : undefined

  const url = '/api/heartbeats-stream'

  const { status, data, error, close, open } = useEventSource(url, ['heartbeat_update'], {
    immediate,
    withCredentials: true,
    autoReconnect: {
      retries: 10,
      delay: 5000,
      onFailed() {
        console.error('[HeartbeatStream] Failed to connect after max retries')
      },
    },
  })

  // Close SSE before page unload to prevent Firefox error:
  // "The connection was interrupted while the page was loading"
  // See: https://bugzilla.mozilla.org/show_bug.cgi?id=833462
  if (import.meta.client) {
    useEventListener('beforeunload', close)
    onScopeDispose(close)
  }

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
