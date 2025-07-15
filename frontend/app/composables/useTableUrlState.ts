import { computed } from 'vue'
import type { Ref, ComputedRef } from 'vue'
import { useRouteQuery } from '@vueuse/router'
import type { SortingState, ColumnFiltersState, VisibilityState } from '@tanstack/vue-table'

interface TableUrlStateOptions {
  defaultView?: 'grouped' | 'ungrouped'
  defaultPageSize?: number
  defaultSortBy?: string
  defaultSortOrder?: 'asc' | 'desc'
}

interface TableUrlState {
  view: Ref<'grouped' | 'ungrouped'>
  page: Ref<number>
  pageSize: Ref<number>
  sortBy: Ref<string>
  sortOrder: Ref<'asc' | 'desc'>
  filters: Ref<Record<string, string | number>>
  hiddenColumns: Ref<string[]>
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

  // Route query parameters
  const viewParam = useRouteQuery('view', defaults.view, { transform: validateView })
  const pageParam = useRouteQuery('page', '1', { 
    transform: (value) => Math.max(1, parseInt(value) || 1) 
  })
  const sizeParam = useRouteQuery('size', defaults.pageSize.toString(), { 
    transform: (value) => validatePageSize(parseInt(value) || defaults.pageSize) 
  })
  const sortParam = useRouteQuery('sort', `${defaults.sortBy}:${defaults.sortOrder}`)
  const filterParam = useRouteQuery('filter', '', { transform: parseFilters })
  const colsParam = useRouteQuery('cols', '', { transform: parseHiddenColumns })
  const refreshParam = useRouteQuery('refresh', '30', { 
    transform: (value) => {
      const num = parseInt(value)
      if (isNaN(num)) return 30
      return [0, 30, 60, 300, 600].includes(num) ? num : 30
    }
  })

  // Factory function for creating URL-synced computed properties
  function createUrlParam<T>(
    param: Ref<T | undefined>,
    defaultValue: T,
    options?: {
      clearCondition?: (value: T) => boolean
      serialize?: (value: T) => any
      deserialize?: (value: any) => T
    }
  ) {
    return computed({
      get: () => {
        const value = param.value
        if (options?.deserialize && value !== undefined) {
          return options.deserialize(value)
        }
        return value !== undefined ? value : defaultValue
      },
      set: (value: T) => {
        const shouldClear = options?.clearCondition 
          ? options.clearCondition(value) 
          : value === defaultValue
        
        if (shouldClear) {
          (param as any).value = undefined
        } else {
          const serialized = options?.serialize ? options.serialize(value) : value
          ;(param as any).value = serialized
        }
      }
    })
  }

  // Use factory function for cleaner URL parameter definitions
  const view = createUrlParam(viewParam, defaults.view)
  
  const page = createUrlParam(pageParam, 1, {
    clearCondition: (value) => value <= 1
  })
  
  const pageSize = createUrlParam(sizeParam as Ref<number | undefined>, defaults.pageSize, {
    serialize: (value) => validatePageSize(value)
  })

  const sortBy = computed<string>({
    get: () => {
      const [field] = sortParam.value.split(':')
      return field || defaults.sortBy
    },
    set: (value) => {
      const currentOrder = sortOrder.value
      const sortString = `${value}:${currentOrder}`
      const defaultSort = `${defaults.sortBy}:${defaults.sortOrder}`
      if (sortString === defaultSort) {
        sortParam.value = undefined as any
      } else {
        sortParam.value = sortString as any
      }
    }
  })

  const sortOrder = computed<'asc' | 'desc'>({
    get: () => {
      const [, order] = sortParam.value.split(':')
      return validateSortOrder(order || defaults.sortOrder)
    },
    set: (value) => {
      const currentBy = sortBy.value
      const sortString = `${currentBy}:${value}`
      const defaultSort = `${defaults.sortBy}:${defaults.sortOrder}`
      if (sortString === defaultSort) {
        sortParam.value = undefined as any
      } else {
        sortParam.value = sortString as any
      }
    }
  })

  const filters = createUrlParam(filterParam as Ref<Record<string, string | number> | undefined>, {}, {
    clearCondition: (value) => Object.keys(value).length === 0,
    serialize: (value) => serializeFilters(value)
  })

  const hiddenColumns = createUrlParam(colsParam as Ref<string[] | undefined>, [], {
    clearCondition: (value) => value.length === 0,
    serialize: (value) => value.join(',')
  })

  const autoRefresh = createUrlParam(refreshParam as Ref<number | undefined>, 30, {
    clearCondition: (value) => value === 30,
    // Special handling for 0 value (disabled state)
    serialize: (value) => value === 0 ? 0 : value
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
    sortBy.value = defaults.sortBy
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