export function useAlertsLiveMode(opts: {
  status: Ref<'idle' | 'pending' | 'success' | 'error'>
  rowSelection: Ref<Record<string, boolean>>
}) {
  const isSilentRefresh = ref(false)
  const isLive = ref(true)
  const { bump: bumpSseToken } = useSseRefreshToken()

  function performSseRefresh() {
    // Skip if already loading or rows selected
    if (opts.status.value === 'pending' || Object.keys(opts.rowSelection.value).length > 0) return

    isSilentRefresh.value = true
    bumpSseToken() // Triggers all components that depend on sseRefreshToken
  }

  const { status: sseStatus, error: sseError, close: sseClose, open: sseOpen } = useAlertStream({
    onNewAlerts: (_count) => { if (isLive.value) performSseRefresh() },
    debounceMs: 2000,
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
