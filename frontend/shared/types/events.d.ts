// Global event type declarations for CustomEvents
// This provides type safety for window.addEventListener and useEventListener

import type { AlertListItem, FlattenedGroupedAlert, CompactGroupedAlert } from '@/types/alerts'

// Extend WindowEventMap to add custom events
declare global {
  interface WindowEventMap {
    // Alert details view event
    'viewAlertDetails': CustomEvent<{
      alertId: string
    }>

    // Alert deletion request event
    'alertDeletionRequest': CustomEvent<{
      mode: 'single' | 'grouped'
      alert?: AlertListItem
      group?: FlattenedGroupedAlert | CompactGroupedAlert
      sourceIp?: string
      targetIp?: string
      totalCount?: number
    }>
  }
}

export {}
