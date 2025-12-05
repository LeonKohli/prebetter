import type { LocationQuery } from 'vue-router'
import type { SortingState, ColumnFiltersState, VisibilityState } from '@tanstack/vue-table'

type PageSize = 10 | 20 | 50 | 100
type SortOrder = 'asc' | 'desc'
type ViewMode = 'grouped' | 'ungrouped'

const VALID_PAGE_SIZES: readonly PageSize[] = [10, 20, 50, 100] as const

export function useNavigableUrlState(options: {
  defaultView?: ViewMode
  defaultPageSize?: number
  defaultSortBy?: string
  defaultSortOrder?: SortOrder
  defaultGroupedSortBy?: string
  defaultUngroupedSortBy?: string
} = {}) {
  const route = useRoute()
  const router = useRouter()
  
  const defaults = {
    view: (options.defaultView || 'grouped') as ViewMode,
    pageSize: (options.defaultPageSize || 100) as PageSize,
    sortBy: options.defaultSortBy || 'detected_at',
    sortOrder: (options.defaultSortOrder || 'desc') as SortOrder,
    groupedSortBy: options.defaultGroupedSortBy || 'detected_at',
    ungroupedSortBy: options.defaultUngroupedSortBy || 'detected_at',
  } as const

  const validatePageSize = (size: number): PageSize => {
    return VALID_PAGE_SIZES.includes(size as PageSize) ? (size as PageSize) : defaults.pageSize
  }

  const validateSortOrder = (order: string): SortOrder => {
    return order === 'asc' ? 'asc' : 'desc'
  }

  const validateView = (view: string): ViewMode => {
    return view === 'ungrouped' ? 'ungrouped' : 'grouped'
  }

  const parseFilters = (filterString: string): Record<string, string | number> => {
    if (!filterString?.trim()) return {}
    
    try {
      const parsed = JSON.parse(filterString)
      
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed as Record<string, string | number>
      }
      
      return {}
    } catch {
      return {}
    }
  }

  const serializeFilters = (filters: Record<string, string | number>): string => {
    const keys = Object.keys(filters)
    if (keys.length === 0) return ''
    return JSON.stringify(filters)
  }

  const parseHiddenColumns = (colString: string): string[] => {
    if (!colString?.trim()) return []
    return colString.split(',').filter(col => col.trim())
  }

  // Update URL using router.push for user actions, router.replace for programmatic updates
  const updateUrl = async (updates: LocationQuery, isUserAction = false) => {
    const currentQuery = { ...route.query }
    const newQuery = { ...currentQuery, ...updates }
    
    // Remove empty values
    Object.keys(newQuery).forEach(key => {
      if (newQuery[key] === '' || newQuery[key] === null || newQuery[key] === undefined) {
        delete newQuery[key]
      }
    })
    
    if (isUserAction) {
      // User action: create history entry
      await router.push({ query: newQuery })
    } else {
      // Programmatic update: replace current entry
      await router.replace({ query: newQuery })
    }
  }

  // Computed refs that read from route.query
  const view = computed<'grouped' | 'ungrouped'>({
    get: () => validateView(route.query.view as string || defaults.view),
    set: (value) => updateUrl({ view: value }, true) // User changing view
  })

  const getDefaultSortString = () => {
    const field = view.value === 'grouped' ? defaults.groupedSortBy : defaults.ungroupedSortBy
    return `${field}:${defaults.sortOrder}`
  }

  const page = computed<number>({
    get: () => Math.max(1, parseInt(String(route.query.page || 1))),
    set: (value) => updateUrl({ page: String(value) }, true) // User changing page
  })

  const pageSize = computed<number>({
    get: () => validatePageSize(parseInt(String(route.query.size || defaults.pageSize))),
    set: (value) => updateUrl({ size: String(value) }, true) // User changing page size
  })

  const sortBy = computed<string>({
    get: () => {
      const sortValue = route.query.sort as string || getDefaultSortString()
      const [field] = sortValue.split(':')
      return field || defaults.sortBy
    },
    set: (value) => {
      const currentOrder = sortOrder.value
      updateUrl({ sort: `${value}:${currentOrder}` }, true) // User sorting
    }
  })

  const sortOrder = computed<'asc' | 'desc'>({
    get: () => {
      const sortValue = route.query.sort as string || getDefaultSortString()
      const [, order] = sortValue.split(':')
      return validateSortOrder(order || defaults.sortOrder)
    },
    set: (value) => {
      const currentBy = sortBy.value
      updateUrl({ sort: `${currentBy}:${value}` }, true) // User sorting
    }
  })

  const filters = computed<Record<string, string | number>>({
    get: () => parseFilters(route.query.filter as string || ''),
    set: (value) => updateUrl({ filter: serializeFilters(value) }, true) // User filtering
  })

  const hiddenColumns = computed<string[]>({
    get: () => parseHiddenColumns(route.query.cols as string || ''),
    set: (value) => updateUrl({ cols: value.join(',') }, true) // User toggling columns
  })

  const autoRefresh = computed<number>({
    get: () => {
      const value = parseInt(String(route.query.refresh || 30))
      return [0, 30, 60, 300, 600].includes(value) ? value : 30
    },
    set: (value) => updateUrl({ refresh: String(value) }, true) // User changing refresh
  })

  // Convert to/from TanStack Table state
  const toSortingState = computed((): SortingState => [{
    id: sortBy.value,
    desc: sortOrder.value === 'desc'
  }])

  const fromSortingState = (state: SortingState, isUserAction = true): void => {
    const firstSort = state[0]
    if (firstSort) {
      const newSort = `${firstSort.id}:${firstSort.desc ? 'desc' : 'asc'}`
      updateUrl({ sort: newSort }, isUserAction)
    }
  }

  const toFilterState = computed((): ColumnFiltersState => {
    return Object.entries(filters.value).map(([id, value]) => ({ id, value }))
  })

  const fromFilterState = (state: ColumnFiltersState, isUserAction = true): void => {
    const newFilters: Record<string, string | number> = {}
    
    for (const filter of state) {
      if (filter.value && (typeof filter.value === 'string' || typeof filter.value === 'number')) {
        newFilters[filter.id] = filter.value
      }
    }
    
    updateUrl({ filter: serializeFilters(newFilters) }, isUserAction)
  }

  const toVisibilityState = computed((): VisibilityState => {
    const visibility: VisibilityState = {}
    
    const allColumnIds = [
      'source_ipv4', 'target_ipv4',
      'detected_at', 'severity', 'classification_text', 'analyzer',
      'total_count'
    ]
    
    for (const col of allColumnIds) {
      visibility[col] = true
    }
    
    for (const col of hiddenColumns.value) {
      visibility[col] = false
    }
    
    return visibility
  })

  const fromVisibilityState = (state: VisibilityState, isUserAction = true): void => {
    const hidden: string[] = []
    for (const [col, visible] of Object.entries(state)) {
      if (!visible) {
        hidden.push(col)
      }
    }
    updateUrl({ cols: hidden.join(',') }, isUserAction)
  }

  const toPaginationState = computed(() => ({
    pageIndex: page.value - 1,
    pageSize: pageSize.value
  }))

  const fromPaginationState = (pageIndex: number, size: number, isUserAction = true): void => {
    updateUrl({
      page: String(pageIndex + 1),
      size: String(size)
    }, isUserAction)
  }

  // High-level update functions
  const updateFilters = (newFilters: Record<string, string | number>, isUserAction = true): void => {
    updateUrl({ filter: serializeFilters(newFilters) }, isUserAction)
  }

  const updateView = (newView: 'grouped' | 'ungrouped', isUserAction = true): void => {
    updateUrl({ view: newView }, isUserAction)
  }

  // Navigate to alert details (always a user action)
  const navigateToDetails = async (details: { sourceIp: string; targetIp: string; classification: string }) => {
    const currentFilters = filters.value

    await router.push({
      query: {
        ...route.query,
        view: 'ungrouped',
        size: '100', // Show 100 alerts by default when viewing group details
        filter: serializeFilters({
          ...currentFilters,
          source_ipv4: details.sourceIp,
          target_ipv4: details.targetIp,
          classification_text: details.classification
        }),
        page: '1',
        sort: 'detected_at:desc'
      }
    })
  }

  const resetToDefaults = (): void => {
    router.replace({ query: {} })
  }

  return {
    view,
    page,
    pageSize,
    sortBy,
    sortOrder,
    filters,
    hiddenColumns,
    autoRefresh,
    
    toSortingState,
    fromSortingState,
    toFilterState,
    fromFilterState,
    toVisibilityState,
    fromVisibilityState,
    toPaginationState,
    fromPaginationState,
    
    updateFilters,
    updateView,
    navigateToDetails,
    resetToDefaults
  }
}
