interface HeartbeatUpdateEvent {
  latest_timestamp: string
  new_count: number
}

interface UseHeartbeatStreamOptions {
  /** Auto-connect on mount (default: true) */
  immediate?: boolean
  /** Initial last known timestamp (ISO format) */
  lastTimestamp?: string | null
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
 * const { isConnected, latestUpdate, totalNewHeartbeats } = useHeartbeatStream({
 *   onNewHeartbeats: () => {
 *     // Refresh the heartbeats table
 *     refreshHeartbeats()
 *   }
 * })
 * </script>
 * ```
 */
export function useHeartbeatStream(options: UseHeartbeatStreamOptions = {}) {
  const {
    immediate = true,
    lastTimestamp: initialLastTimestamp = null,
    onNewHeartbeats,
    debounceMs = 1000
  } = options

  // Debounced callback for new heartbeats - batches rapid updates
  const debouncedOnNewHeartbeats = onNewHeartbeats
    ? useDebounceFn(onNewHeartbeats, debounceMs)
    : undefined

  // Track the last known timestamp for reconnection
  const lastKnownTimestamp = ref<string | null>(initialLastTimestamp)

  // Total count of new heartbeats since stream started
  const totalNewHeartbeats = ref(0)

  // Static URL - timestamp is only for initial connection context, NOT reactive
  // If we made this reactive, every SSE event would change the URL and trigger reconnection!
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

  // When we receive a new update, update tracking and notify
  watch(latestUpdate, (update) => {
    if (!update) return

    // Update last known timestamp for reconnection
    lastKnownTimestamp.value = update.latest_timestamp

    // Accumulate new heartbeat count
    totalNewHeartbeats.value += update.new_count

    // Notify callback (debounced) - this triggers table refresh
    debouncedOnNewHeartbeats?.()
  })

  // Connection state helpers
  const isConnected = computed(() => status.value === 'OPEN')
  const isConnecting = computed(() => status.value === 'CONNECTING')

  // Reset the new heartbeats counter (call after refresh)
  function clearNewHeartbeatCount() {
    totalNewHeartbeats.value = 0
  }

  // Set last known timestamp (useful when loading initial data)
  function setLastKnownTimestamp(timestamp: string | null) {
    lastKnownTimestamp.value = timestamp
  }

  return {
    // Connection state
    status,
    isConnected,
    isConnecting,
    error,

    // Update data
    latestUpdate,
    totalNewHeartbeats,
    lastKnownTimestamp: readonly(lastKnownTimestamp),

    // Actions
    close,
    open,
    clearNewHeartbeatCount,
    setLastKnownTimestamp,
  }
}
