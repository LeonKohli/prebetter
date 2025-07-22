import type { Ref, ComputedRef, WritableComputedRef } from 'vue'
import { useRouteQuery } from '@vueuse/router'
import type { SortingState, ColumnFiltersState, VisibilityState } from '@tanstack/vue-table'

interface TableUrlStateOptions {
  defaultView?: 'grouped' | 'ungrouped'
  defaultPageSize?: number
  defaultSortBy?: string
  defaultSortOrder?: 'asc' | 'desc'
  defaultGroupedSortBy?: string
  defaultUngroupedSortBy?: string
}

interface TableUrlState {
  view: Ref<'grouped' | 'ungrouped'>
  page: Ref<number>
  pageSize: Ref<number>
  sortBy: WritableComputedRef<string>
  sortOrder: WritableComputedRef<'asc' | 'desc'>
  filters: WritableComputedRef<Record<string, string | number>>
  hiddenColumns: WritableComputedRef<string[]>
  autoRefresh: Ref<number>
  
  toSortingState: ComputedRef<SortingState>
  fromSortingState: (state: SortingState) => void
  toFilterState: ComputedRef<ColumnFiltersState>
  fromFilterState: (state: ColumnFiltersState) => void
  toVisibilityState: ComputedRef<VisibilityState>
  fromVisibilityState: (state: VisibilityState) => void
  toPaginationState: ComputedRef<{ pageIndex: number; pageSize: number }>
  fromPaginationState: (pageIndex: number, size: number) => void
  
  resetToDefaults: () => void
}

type PageSize = 10 | 20 | 50 | 100
type SortOrder = 'asc' | 'desc'
type ViewMode = 'grouped' | 'ungrouped'

const VALID_PAGE_SIZES: readonly PageSize[] = [10, 20, 50, 100] as const

export function useTableUrlState(options: TableUrlStateOptions = {}): TableUrlState {
  const defaults = {
    view: (options.defaultView || 'grouped') as ViewMode,
    pageSize: (options.defaultPageSize || 100) as PageSize,
    sortBy: options.defaultSortBy || 'detected_at',
    sortOrder: (options.defaultSortOrder || 'desc') as SortOrder,
    groupedSortBy: options.defaultGroupedSortBy || 'total_count',
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
    if (!filterString || !filterString.trim()) return {}
    
    try {
      const parsed = JSON.parse(decodeURIComponent(filterString))
      
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        return {}
      }

      const validFilters: Record<string, string | number> = {}
      
      for (const [key, value] of Object.entries(parsed)) {
        if (typeof key === 'string' && (typeof value === 'string' || typeof value === 'number')) {
          validFilters[key] = value
        }
      }
      
      return validFilters
    } catch {
      console.warn('Invalid filter parameter format')
      return {}
    }
  }

  const serializeFilters = (filters: Record<string, string | number>): string => {
    const keys = Object.keys(filters)
    if (keys.length === 0) return ''
    return encodeURIComponent(JSON.stringify(filters))
  }

  const parseHiddenColumns = (colString: string): string[] => {
    if (!colString || typeof colString !== 'string' || !colString.trim()) return []
    return colString.split(',').filter(col => typeof col === 'string' && col.trim().length > 0)
  }

  // Route query parameters with transforms
  const viewParam = useRouteQuery('view', defaults.view, { 
    transform: validateView 
  })
  
  const pageParam = useRouteQuery('page', 1, { 
    transform: (value) => Math.max(1, parseInt(String(value)) || 1) 
  })
  
  const sizeParam = useRouteQuery('size', defaults.pageSize, { 
    transform: (value) => validatePageSize(parseInt(String(value)) || defaults.pageSize) 
  })
  
  const sortParam = useRouteQuery('sort', `${defaults.sortBy}:${defaults.sortOrder}`)
  
  const filterParam = useRouteQuery<string>('filter', '')
  
  const colsParam = useRouteQuery<string>('cols', '', { 
    transform: (value) => {
      if (!value || typeof value !== 'string') return ''
      return value
    }
  })
  
  const refreshParam = useRouteQuery('refresh', 30, { 
    transform: (value) => {
      const num = parseInt(String(value))
      if (isNaN(num)) return 30
      return [0, 30, 60, 300, 600].includes(num) ? num : 30
    }
  })

  // Direct computed properties - no factory pattern needed
  const view = viewParam as Ref<'grouped' | 'ungrouped'>
  const page = pageParam as Ref<number>
  const pageSize = sizeParam as Ref<number>
  const autoRefresh = refreshParam as Ref<number>
  
  // hiddenColumns needs special handling for array conversion
  const hiddenColumns = computed<string[]>({
    get: () => parseHiddenColumns(colsParam.value),
    set: (value) => {
      colsParam.value = value.length > 0 ? value.join(',') : ''
    }
  })
  
  // Filters need special handling for serialization
  const filters = computed<Record<string, string | number>>({
    get: () => parseFilters(filterParam.value),
    set: (value) => {
      filterParam.value = Object.keys(value).length > 0 ? serializeFilters(value) : ''
    }
  })

  // Parse sort parameter into separate fields
  const sortBy = computed<string>({
    get: () => {
      const [field] = sortParam.value.split(':')
      return field || defaults.sortBy
    },
    set: (value) => {
      const currentOrder = sortOrder.value
      sortParam.value = `${value}:${currentOrder}`
    }
  })

  const sortOrder = computed<'asc' | 'desc'>({
    get: () => {
      const [, order] = sortParam.value.split(':')
      return validateSortOrder(order || defaults.sortOrder)
    },
    set: (value) => {
      const currentBy = sortBy.value
      sortParam.value = `${currentBy}:${value}`
    }
  })

  // TanStack Table integration helpers
  const toSortingState = computed((): SortingState => [{
    id: sortBy.value,
    desc: sortOrder.value === 'desc'
  }])

  const fromSortingState = (state: SortingState): void => {
    const firstSort = state[0]
    if (firstSort) {
      sortBy.value = firstSort.id
      sortOrder.value = firstSort.desc ? 'desc' : 'asc'
    }
  }

  const toFilterState = computed((): ColumnFiltersState => {
    return Object.entries(filters.value).map(([id, value]) => ({ id, value }))
  })

  const fromFilterState = (state: ColumnFiltersState): void => {
    const newFilters: Record<string, string | number> = {}
    
    for (const filter of state) {
      if (filter.value !== undefined && filter.value !== '') {
        if (typeof filter.value === 'string' || typeof filter.value === 'number') {
          newFilters[filter.id] = filter.value
        }
      }
    }
    
    // Update filters directly - useRouteQuery will handle serialization
    filters.value = newFilters
  }

  const toVisibilityState = computed((): VisibilityState => {
    const visibility: VisibilityState = {}
    
    // Define all possible column IDs for both views
    const allColumnIds = [
      // Common columns
      'source_ipv4', 'target_ipv4',
      // Ungrouped only
      'detected_at', 'severity', 'classification_text', 'analyzer',
      // Grouped only  
      'total_count'
    ]
    
    // Set all columns as visible by default
    for (const col of allColumnIds) {
      visibility[col] = true
    }
    
    // Set hidden columns to false
    for (const col of hiddenColumns.value) {
      visibility[col] = false
    }
    
    return visibility
  })

  const fromVisibilityState = (state: VisibilityState): void => {
    const hidden: string[] = []
    for (const [col, visible] of Object.entries(state)) {
      if (!visible) {
        hidden.push(col)
      }
    }
    // Update hiddenColumns which will update colsParam
    hiddenColumns.value = hidden
  }

  const toPaginationState = computed(() => ({
    pageIndex: page.value - 1, // Convert to 0-indexed
    pageSize: pageSize.value
  }))

  const fromPaginationState = (pageIndex: number, size: number): void => {
    page.value = pageIndex + 1 // Convert to 1-indexed
    pageSize.value = size
  }

  const resetToDefaults = (): void => {
    view.value = defaults.view
    page.value = 1
    pageSize.value = defaults.pageSize
    sortBy.value = view.value === 'grouped' ? defaults.groupedSortBy : defaults.ungroupedSortBy
    sortOrder.value = defaults.sortOrder
    filters.value = {}
    hiddenColumns.value = []
    autoRefresh.value = 30
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
    
    resetToDefaults
  }
}