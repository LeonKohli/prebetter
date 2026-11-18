import { getPresetRange, isRelativePreset, getActivePresetId, filterDate } from '@/utils/datePresets'

/**
 * The time range of the current view: the active preset, the explicit dates of the filter, or a sliding
 * 24 hours. A relative range moves on with every refresh signal of the live stream.
 */
export function useAlertDateRange(urlState: ReturnType<typeof useNavigableUrlState>) {
  const { token: sseRefreshToken } = useSseRefreshToken()

  return computed(() => {
    const presetId = getActivePresetId(urlState.filters.value)
    const filters = urlState.filters.value

    if (presetId) {
      if (isRelativePreset(presetId)) {
        void sseRefreshToken.value
      }
      const range = getPresetRange(presetId)
      return { start: range.from, end: range.to }
    }

    if (filters.start_date && filters.end_date) {
      return { start: filterDate(filters.start_date), end: filterDate(filters.end_date) }
    }

    // Default: sliding 24h window - needs token dependency for SSE refresh
    void sseRefreshToken.value
    return { start: new Date(Date.now() - 24 * 60 * 60 * 1000), end: new Date() }
  })
}
