# UX Loading States Analysis - AlertsTable Component

## Executive Summary

This analysis examines the loading states and user feedback during async operations in the AlertsTable component, focusing on skeleton loaders, view transitions, and error handling.

## Current Implementation Analysis

### 1. Skeleton Loader Implementation

**Timing & Conditions:**
- Shows skeleton on initial load: `status === 'idle' || (status === 'pending' && !data)`
- Shows skeleton when changing views: `isChangingView` flag
- Displays 20 skeleton rows with animated pulse effect
- Each skeleton row matches the column count dynamically

**Code Reference (AlertsTable.vue:404-410):**
```vue
<template v-if="status === 'idle' || (status === 'pending' && !data) || isChangingView">
  <TableRow v-for="i in 20" :key="`skeleton-${i}`" class="h-11 border-b border-border">
    <TableCell v-for="j in columns.length" :key="`skeleton-${i}-${j}`" class="py-2 px-4">
      <div class="h-4 bg-muted animate-pulse rounded" />
    </TableCell>
  </TableRow>
</template>
```

### 2. Loading States for Async Operations

**Loading Overlay:**
- Shows semi-transparent overlay during user-initiated loads
- Excludes auto-refresh operations (silent refresh)
- Computed property: `showLoadingOverlay`
- Fade transition with 150ms duration

**Code Reference (AlertsTable.vue:148-150):**
```vue
const showLoadingOverlay = computed(() => 
  status.value === 'pending' && data.value !== undefined && !isSilentRefresh.value
)
```

### 3. Toggle Button Behavior During Transitions

**Current Implementation:**
- Toggle button IS disabled during pending operations
- Uses `:disabled="pending"` prop
- Prevents user interaction during view transitions

**Code Reference (AlertsToolbar.vue:83):**
```vue
<Button
  variant="outline"
  size="sm"
  @click="$emit('toggleView')"
  class="h-8 px-3 text-xs font-medium border-border hover:bg-background transition-all"
  :disabled="pending"
>
```

### 4. Batch Update Operation

**Implementation:**
- Uses `updateBatch` method to prevent race conditions
- Atomic updates via router.push/replace
- Proper state synchronization with URL

**Code Reference (AlertsTable.vue:269-277):**
```vue
await urlState.updateBatch({
  view: newView,
  page: 1,
  sortBy: newView === 'grouped' ? 'total_count' : 'detected_at',
  sortOrder: 'desc',
  filters: currentFilters
}, true) // true = user action
```

### 5. Error Handling

**Current Implementation:**
- Error state only shows when not actively fetching
- Simple error message in table body
- No detailed error information provided

**Code Reference (AlertsTable.vue:134-138):**
```vue
const displayError = computed(() => {
  // Only show errors when we're not actively fetching
  if (status.value === 'pending' || !error.value) return null
  return error.value
})
```

### 6. Accessibility Features

**Current Implementation:**
- Basic ARIA attributes on table: `role="table"`, `aria-label="Security alerts table"`
- Loading overlay has accessibility attributes:
  - `role="status"`
  - `aria-live="polite"`
  - `aria-busy="true"`
  - `aria-label="Loading alerts"`
- Empty state has `aria-live="polite"`

## Issues Identified

### 1. Limited Error Feedback
- Generic error message doesn't help users understand what went wrong
- No retry mechanism visible in UI
- No differentiation between network errors vs server errors

### 2. Accessibility Gaps
- No focus management during view transitions
- No announcement when view change completes
- Skeleton loader lacks proper ARIA labels
- No keyboard shortcuts for common actions

### 3. Visual Feedback
- No progress indicator for long-running operations
- Skeleton loader doesn't match actual data layout precisely
- No visual indication of which view is being loaded

### 4. Loading State Inconsistencies
- Different loading patterns for initial vs subsequent loads
- No loading indicator in pagination buttons

## Recommendations

### 1. Enhanced Error Handling
```vue
// Add detailed error messages
const errorMessage = computed(() => {
  if (!displayError.value) return null
  
  const error = displayError.value
  if (error.statusCode === 504) return "Request timed out. Please try again."
  if (error.statusCode === 500) return "Server error. Our team has been notified."
  if (!navigator.onLine) return "No internet connection. Please check your network."
  return "Failed to load alerts. Please refresh the page."
})

// Add retry button
<Button @click="refresh" size="sm">
  <Icon name="lucide:refresh-cw" class="mr-2" />
  Retry
</Button>
```

### 2. Improved Accessibility
```vue
// Add live region for announcements
<div class="sr-only" aria-live="assertive" aria-atomic="true">
  {{ loadingAnnouncement }}
</div>

// Manage focus on view change
watch(isChangingView, (changing) => {
  if (!changing && tableRef.value) {
    tableRef.value.focus()
  }
})

// Add keyboard shortcuts
const handleKeyboard = (e: KeyboardEvent) => {
  if (e.key === 'r' && (e.metaKey || e.ctrlKey)) {
    e.preventDefault()
    refresh()
  }
}
```

### 3. Enhanced Visual Feedback
```vue
// Add view transition indicator
<Transition name="slide-fade">
  <div v-if="isChangingView" class="flex items-center gap-2 text-sm text-muted-foreground">
    <Icon name="lucide:loader-2" class="animate-spin" />
    Switching to {{ urlState.view.value === 'grouped' ? 'individual' : 'grouped' }} view...
  </div>
</Transition>

// Improve skeleton to match data structure
<template v-if="isGrouped && isChangingView">
  <!-- Grouped skeleton with proper row heights and grouping indicators -->
</template>
```

### 4. Loading State Consistency
```vue
// Add loading states to pagination
<Button
  :disabled="urlState.page.value === 1 || pending"
  :class="{ 'opacity-50': pending }"
>
  <Icon v-if="pending" name="lucide:loader-2" class="animate-spin" />
  <Icon v-else name="lucide:chevron-left" />
  Previous
</Button>

// Add progress for long operations
<Progress v-if="loadingDuration > 2000" :value="loadingProgress" class="h-1" />
```

### 5. Focus Management
```vue
// Trap focus during loading for keyboard users
const trapFocus = (e: KeyboardEvent) => {
  if (isChangingView.value && e.key === 'Tab') {
    e.preventDefault()
    // Keep focus on toggle button
  }
}
```

### 6. Performance Optimizations
```vue
// Preload view data on hover
const preloadView = () => {
  if (!pending.value) {
    const alternateView = isGrouped.value ? 'ungrouped' : 'grouped'
    // Prefetch data for quick switching
    $fetch(alternateView === 'grouped' ? '/api/alerts/groups' : '/api/alerts')
  }
}
```

## Implementation Priority

1. **High Priority:**
   - Fix error handling with clear messages and retry
   - Add proper ARIA announcements for view changes
   - Ensure toggle button remains disabled during transitions

2. **Medium Priority:**
   - Improve skeleton loader to match data structure
   - Add focus management for keyboard users
   - Add loading indicators to pagination controls

3. **Low Priority:**
   - Add keyboard shortcuts
   - Implement view preloading
   - Add progress indicators for long operations

## Conclusion

The current implementation handles the basic loading states well, with proper skeleton loaders and disabled controls during transitions. The batch update mechanism successfully prevents race conditions. However, there are opportunities to improve error handling, accessibility, and visual feedback to create a more polished user experience.

Key strengths:
- Skeleton loader implementation
- Toggle button properly disabled during transitions
- Batch updates prevent race conditions
- Basic accessibility attributes in place

Areas for improvement:
- More informative error handling
- Better accessibility with focus management and announcements
- Enhanced visual feedback during transitions
- Consistent loading states across all interactive elements