interface UseHeartbeatStreamOptions {
  immediate?: boolean
  onNewHeartbeats?: () => void | Promise<void>
  debounceMs?: number
}

export function useHeartbeatStream(options: UseHeartbeatStreamOptions = {}) {
  const { immediate = true, onNewHeartbeats, debounceMs = 1000 } = options

  const debouncedOnNewHeartbeats = onNewHeartbeats
    ? useDebounceFn(onNewHeartbeats, debounceMs)
    : undefined

  const onSseGiveUp = useSseSessionGuard()

  const url = '/api/heartbeats-stream'

  const { status, data, error, close, open } = useEventSource<['heartbeat_update'], string>(url, ['heartbeat_update'], {
    immediate,
    withCredentials: true,
    autoReconnect: {
      retries: 10,
      delay: 5000,
      onFailed() {
        console.error('[HeartbeatStream] Failed to connect after max retries')
        onSseGiveUp().catch(err => console.error('[HeartbeatStream] Session check failed:', err))
      },
    },
  })

  if (import.meta.client) {
    useEventListener('beforeunload', close)
    onScopeDispose(close)
  }

  watch(data, (raw) => {
    if (!raw) return
    return debouncedOnNewHeartbeats?.()
  })

  return {
    status,
    error,
    close,
    open,
  }
}
