export function useAlertsLiveMode(opts: {
  status: Ref<'idle' | 'pending' | 'success' | 'error'>
  rowSelection: Ref<Record<string, boolean>>
  requireIps?: Ref<boolean>
}) {
  const isSilentRefresh = ref(false)
  const isLive = ref(true)
  const { bump: bumpSseToken } = useSseRefreshToken()

  function performSseRefresh() {
    if (opts.status.value === 'pending' || Object.keys(opts.rowSelection.value).length > 0) return

    isSilentRefresh.value = true
    bumpSseToken()
  }

  const { status: sseStatus, error: sseError, close: sseClose, open: sseOpen } = useAlertStream({
    onNewAlerts: (_count) => { if (isLive.value) performSseRefresh() },
    debounceMs: 2000,
    requireIps: opts.requireIps,
  })

  function toggleLive() {
    isLive.value = !isLive.value
    if (isLive.value) sseOpen()
    else sseClose()
  }

  const showLoadingOverlay = computed(() => opts.status.value === 'pending' && !isSilentRefresh.value)

  return {
    isLive, isSilentRefresh, sseStatus, sseError, showLoadingOverlay,
    toggleLive, resetSilentRefresh: () => { isSilentRefresh.value = false },
  }
}
