import { provide, inject, type InjectionKey, type ComputedRef, type Ref } from 'vue'
import type { Table } from '@tanstack/vue-table'
import type { AlertListItem, FlattenedGroupedAlert } from '~/types/alerts'
import type { useNavigableUrlState } from './useNavigableUrlState'

export interface AlertTableContext {
  urlState: ReturnType<typeof useNavigableUrlState>
  table: Table<AlertListItem | FlattenedGroupedAlert>
  isGrouped: ComputedRef<boolean>
  pending: Ref<boolean>
}

const AlertTableKey = Symbol('AlertTableContext') as InjectionKey<AlertTableContext>

export function provideAlertTableContext(context: AlertTableContext) {
  provide(AlertTableKey, context)
}

export function useAlertTableContext() {
  const context = inject(AlertTableKey)
  if (!context) {
    throw new Error('AlertTableContext not provided. Make sure to call provideAlertTableContext in a parent component.')
  }
  return context
}