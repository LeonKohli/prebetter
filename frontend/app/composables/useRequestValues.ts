import type { RequestFilterField, RequestValue } from '~~/shared/types/alerts'

const SUGGESTIONS = 50

/**
 * The most common values of one request header in the range of the current view, for the filter's
 * suggestions. Nothing is fetched until `load` is called, because the panel may never be opened.
 */
export function useRequestValues(field: RequestFilterField) {
  const { urlState } = useAlertTableContext()
  const range = useAlertDateRange(urlState)

  const search = ref('')
  const debouncedSearch = refDebounced(search, 250)

  const query = computed(() => ({
    field,
    q: debouncedSearch.value.trim(),
    start_date: range.value.start.toISOString(),
    end_date: range.value.end.toISOString(),
    size: SUGGESTIONS,
  }))

  // The range slides with the live stream, so the query is read when `load` runs, not watched.
  const { data, status, error, execute } = useFetch<RequestValue[]>('/api/reference/request-values', {
    key: `request-values-${field}`,
    query,
    default: () => [],
    lazy: true,
    immediate: false,
    watch: false,
  })

  return { values: data, status, error, search, debouncedSearch, load: execute }
}
