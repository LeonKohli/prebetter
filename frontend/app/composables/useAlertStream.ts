interface UseAlertStreamOptions {
  immediate?: boolean
  onNewAlerts?: (count: number) => void
  debounceMs?: number
  requireIps?: Ref<boolean>
}

export function useAlertStream(options: UseAlertStreamOptions = {}) {
  const { immediate = true, onNewAlerts, debounceMs = 1000, requireIps } = options

  const debouncedOnNewAlerts = onNewAlerts
    ? useDebounceFn(onNewAlerts, debounceMs)
    : undefined

  const onSseGiveUp = useSseSessionGuard()

  const url = computed(() => {
    const base = '/api/alerts-stream'
    if (requireIps && !requireIps.value) {
      return `${base}?require_ips=false`
    }
    return base
  })

  const { status, data, error, close, open } = useEventSource<['alerts'], string>(url, ['alerts'], {
    immediate,
    withCredentials: true,
    autoReconnect: {
      retries: 10,
      delay: 5000,
      onFailed() {
        console.error('[AlertStream] Failed to reconnect after max retries')
        onSseGiveUp().catch(err => console.error('[AlertStream] Session check failed:', err))
      },
    },
  })

  if (import.meta.client) {
    useEventListener('beforeunload', close)
    onScopeDispose(close)
  }

  watch(data, async (raw) => {
    if (!raw) return
    let notification: unknown
    try {
      notification = JSON.parse(raw)
    } catch {
      return
    }
    if (typeof notification !== 'object' || notification === null ||
      !('count' in notification) || typeof notification.count !== 'number') return
    await debouncedOnNewAlerts?.(notification.count)
  })

  return {
    status,
    error,
    close,
    open,
  }
}
