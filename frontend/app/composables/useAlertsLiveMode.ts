/**
 * Live mode (SSE) composable for alerts table.
 */
export function useAlertsLiveMode(opts: {
  status: Ref<'idle' | 'pending' | 'success' | 'error'>
  rowSelection: Ref<Record<string, boolean>>
  refresh: () => Promise<void>
  getActivePresetId: () => DatePresetId | undefined
  triggerRelativeRefresh: () => void
}) {
  const isSilentRefresh = ref(false)
  const isLive = ref(true)

  async function performSseRefresh() {
    if (opts.status.value === 'pending' || Object.keys(opts.rowSelection.value).length > 0) return

    const presetId = opts.getActivePresetId()
    if (presetId && isRelativePreset(presetId)) {
      isSilentRefresh.value = true
      opts.triggerRelativeRefresh()
      return
    }

    try {
      isSilentRefresh.value = true
      await opts.refresh()
    } finally {
      isSilentRefresh.value = false
    }
  }

  const { status: sseStatus, error: sseError, close: sseClose, open: sseOpen } = useAlertStream({
    onNewAlerts: () => { if (isLive.value) performSseRefresh() },
    debounceMs: 2000,
  })

  function toggleLive() {
    isLive.value = !isLive.value
    isLive.value ? (sseOpen(), opts.refresh()) : sseClose()
  }

  const showLoadingOverlay = computed(() => opts.status.value === 'pending' && !isSilentRefresh.value)

  return {
    isLive, isSilentRefresh, sseStatus, sseError, showLoadingOverlay,
    toggleLive, resetSilentRefresh: () => { isSilentRefresh.value = false },
  }
}
