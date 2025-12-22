interface UseAlertStreamOptions {
  immediate?: boolean
  onNewAlerts?: (count: number) => void
  debounceMs?: number
}

interface AlertNotification {
  count: number
  latest_id: number
}

export function useAlertStream(options: UseAlertStreamOptions = {}) {
  const { immediate = true, onNewAlerts, debounceMs = 1000 } = options

  const debouncedOnNewAlerts = onNewAlerts
    ? useDebounceFn(onNewAlerts, debounceMs)
    : undefined

  const url = '/api/alerts-stream'

  const { status, data, error, close, open } = useEventSource(url, ['alerts'], {
    immediate,
    withCredentials: true,
    autoReconnect: {
      retries: 10,
      delay: 5000,
      onFailed() {
        console.error('[AlertStream] Failed to reconnect after max retries')
      },
    },
  })

  if (import.meta.client) {
    useEventListener('beforeunload', close)
    onScopeDispose(close)
  }

  watch(data, (raw) => {
    if (!raw) return
    try {
      const notification = JSON.parse(raw) as AlertNotification
      debouncedOnNewAlerts?.(notification.count)
    } catch {}
  })

  return {
    status,
    error,
    close,
    open,
  }
}
