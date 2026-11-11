import {
  columnFilteringFeature,
  columnVisibilityFeature,
  metaHelper,
  rowPaginationFeature,
  rowSortingFeature,
  tableFeatures,
} from '@tanstack/vue-table'

/** Typed callbacks the table hands to its column definitions through `table.options.meta`. */
export interface AlertTableMeta {
  onViewDetails?: (alertId: string) => void
}

// Sorting, filtering and pagination run on the server (manual mode), so no row-model slots are registered.
export const alertTableFeatures = tableFeatures({
  columnFilteringFeature,
  columnVisibilityFeature,
  rowPaginationFeature,
  rowSortingFeature,
  tableMeta: metaHelper<AlertTableMeta>(),
})

export type AlertTableFeatures = typeof alertTableFeatures
export type AlertTableRow = GroupedAlert | AlertListItem
