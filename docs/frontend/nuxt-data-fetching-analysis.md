# Nuxt 3 Data Fetching Analysis

## Executive Summary

This document analyzes the data fetching patterns in the Prebetter frontend application against Nuxt 3 best practices. The application demonstrates a mature implementation with proper server-side rendering support, API proxy pattern, and sophisticated caching strategies. However, there are opportunities for improvement in error boundary implementation and optimistic updates.

## Current Data Fetching Architecture

### 1. API Proxy Pattern

The application implements a secure API proxy pattern through `/server/api/[...].ts`:

```typescript
// Server-side proxy that injects JWT tokens from secure sessions
export default defineEventHandler(async (event: H3Event) => {
  const session = await getUserSession(event)
  const apiToken = session.secure?.apiToken
  
  // Proxy request with authentication
  const response = await $fetch.raw(target, {
    headers: apiToken ? { 'Authorization': `Bearer ${apiToken}` } : {},
    ...fetchOptions
  })
})
```

**Strengths:**
- JWT tokens never exposed to client
- Centralized authentication handling
- Proper error forwarding with status codes
- Request method and body preservation

**Weaknesses:**
- No request/response logging for debugging
- Missing retry logic at proxy level
- No request timeout configuration

### 2. Data Fetching Patterns

#### useFetch Usage (Recommended Pattern)

The application correctly uses `useFetch` for SSR-compatible data fetching:

```vue
<!-- AlertsTable.vue -->
const { data, pending, error, refresh, status, execute } = await useFetch<GroupedAlertResponse | AlertListResponse>(
  fetchUrl,
  {
    key: fetchKey,          // Dynamic key for cache management
    query: fetchQuery,      // Reactive query parameters
    server: true,           // SSR enabled
    lazy: false,            // Immediate execution
    dedupe: 'defer',        // Prevent request cancellation
    watch: false            // Manual reactivity control
  }
)
```

**Best Practices Observed:**
- Dynamic keys prevent NS_BINDING_ABORTED errors
- Computed query parameters for reactivity
- Proper TypeScript typing for responses
- Manual watch control for performance

#### $fetch Usage (Client-Side Actions)

The application correctly uses `$fetch` for client-side mutations:

```vue
<!-- login.vue -->
await $fetch('/api/auth/login', {
  method: 'POST',
  body: {
    username: username.value,
    password: password.value,
  },
})
```

**Appropriate Usage:**
- Form submissions
- DELETE operations
- Non-SSR critical paths

### 3. Caching Strategy Evaluation

#### Key-Based Caching

The application implements sophisticated key-based caching:

```typescript
// Comprehensive key includes all state affecting data
const fetchKey = computed(() => {
  const stateHash = JSON.stringify({
    view: urlState.view.value,
    page: urlState.page.value,
    pageSize: urlState.pageSize.value,
    sortBy: urlState.sortBy.value,
    sortOrder: urlState.sortOrder.value,
    filters: urlState.filters.value,
  })
  return `alerts-${btoa(stateHash)}`
})
```

**Strengths:**
- Unique keys for different data states
- Base64 encoding prevents key conflicts
- Excludes non-data-affecting state (hiddenColumns, autoRefresh)

**Weaknesses:**
- No explicit cache TTL configuration
- Missing `getCachedData` implementation for fine-grained control
- No cache invalidation strategy

#### URL State Synchronization

The application syncs table state with URL for shareable links:

```typescript
const urlState = useTableUrlState({
  defaultView: 'grouped',
  defaultPageSize: 100,
  defaultSortBy: 'detected_at',
  defaultSortOrder: 'desc',
})
```

**Benefits:**
- Shareable URLs maintain full table state
- Back/forward navigation preserves state
- Deep linking to specific views

### 4. Error Handling Assessment

#### Global 401 Handler

```typescript
// api-guard.client.ts
globalThis.$fetch = $fetch.create({
  onResponseError({ response }) {
    if (response.status === 401) {
      const { clear } = useUserSession()
      clear().then(() => navigateTo('/login'))
    }
  }
})
```

**Strengths:**
- Automatic session cleanup on 401
- Consistent unauthorized handling
- Client-side only (appropriate)

#### Component-Level Error Handling

```vue
<!-- UserManagementTable.vue -->
<template v-else-if="error">
  <TableRow>
    <TableCell colspan="6" class="text-center py-8 text-destructive">
      Error loading users: {{ error.message }}
    </TableCell>
  </TableRow>
</template>
```

**Weaknesses:**
- No retry mechanisms at component level
- Limited error context (no error codes)
- No error boundary implementation

### 5. Loading States

#### Multi-Level Loading States

```vue
<!-- AlertsTable.vue -->
// Initial load skeleton
<template v-if="status === 'idle' || (status === 'pending' && !data) || isChangingView">
  <TableRow v-for="i in 20" :key="`skeleton-${i}`">
    <!-- Skeleton UI -->
  </TableRow>
</template>

// Refresh overlay (preserves existing data)
<div v-if="showLoadingOverlay" class="absolute inset-0 bg-background/40 z-10" />
```

**Strengths:**
- Skeleton UI for initial loads
- Overlay for refreshes (preserves content)
- Silent refresh for auto-updates
- View change indicators

### 6. Performance Implications

#### Debounced Execution

```typescript
watchDebounced(
  fetchKey,
  () => execute(),
  { debounce: 50 } // Batch multiple state changes
)
```

**Benefits:**
- Prevents rapid-fire requests
- Batches related state changes
- Reduces server load

#### Auto-Refresh Implementation

```typescript
const { pause, resume, isActive } = useIntervalFn(
  performAutoRefresh,
  autoRefreshInterval,
  { immediate: false }
)

// Document visibility handling
watch(documentVisibility, async (visibility) => {
  if (visibility === 'hidden') {
    stopAutoRefresh()
  } else if (visibility === 'visible' && autoRefreshEnabled.value) {
    startAutoRefresh()
    await performAutoRefresh() // Immediate refresh on tab focus
  }
})
```

**Optimizations:**
- Pauses when tab not visible
- Skips refresh during user selections
- Immediate refresh on tab return

## Best Practice Recommendations

### 1. Implement getCachedData for Fine Control

```typescript
const { data } = await useFetch('/api/alerts', {
  getCachedData: (key, nuxtApp, ctx) => {
    // Don't use cache on manual refresh
    if (ctx.cause === 'refresh:manual') return undefined
    
    // Use cache for auto-refresh if data is fresh
    if (ctx.cause === 'refresh:hook') {
      const cached = nuxtApp.payload.data[key]
      if (cached && Date.now() - cached.timestamp < 30000) {
        return cached.data
      }
    }
    
    return nuxtApp.payload.data[key]
  }
})
```

### 2. Add Error Boundaries

```vue
<!-- components/ErrorBoundary.vue -->
<template>
  <div v-if="error" class="error-boundary">
    <Alert variant="destructive">
      <AlertTitle>Something went wrong</AlertTitle>
      <AlertDescription>{{ error.message }}</AlertDescription>
      <Button @click="retry" class="mt-2">Try Again</Button>
    </Alert>
  </div>
  <slot v-else />
</template>

<script setup>
const error = ref(null)
const retry = () => {
  error.value = null
  // Trigger data refresh in child components
}

onErrorCaptured((err) => {
  error.value = err
  return false
})
</script>
```

### 3. Implement Optimistic Updates

```typescript
// For user actions like delete
const optimisticDelete = async (userId: string) => {
  // Optimistically remove from UI
  const originalData = data.value
  data.value = {
    ...data.value,
    items: data.value.items.filter(u => u.id !== userId)
  }
  
  try {
    await $fetch(`/api/users/${userId}`, { method: 'DELETE' })
    // Refresh to ensure consistency
    await refresh()
  } catch (error) {
    // Rollback on error
    data.value = originalData
    throw error
  }
}
```

### 4. Add Request Deduplication

```typescript
// Create a composable for deduped fetching
const pendingRequests = new Map()

export const useDedupedFetch = (url: string, options = {}) => {
  const key = computed(() => `${url}-${JSON.stringify(options.query || {})}`)
  
  if (pendingRequests.has(key.value)) {
    return pendingRequests.get(key.value)
  }
  
  const promise = useFetch(url, options)
  pendingRequests.set(key.value, promise)
  
  promise.finally(() => {
    pendingRequests.delete(key.value)
  })
  
  return promise
}
```

### 5. Implement Race Condition Handling

```typescript
// Use abort controllers for search/filter operations
const abortController = ref<AbortController>()

const search = async (query: string) => {
  // Cancel previous request
  abortController.value?.abort()
  abortController.value = new AbortController()
  
  try {
    const { data } = await $fetch('/api/search', {
      query: { q: query },
      signal: abortController.value.signal
    })
    return data
  } catch (error) {
    if (error.name !== 'AbortError') throw error
  }
}
```

### 6. Add Transform Functions for Data Normalization

```typescript
const { data } = await useFetch('/api/alerts', {
  transform: (response) => {
    // Normalize data structure
    return {
      items: response.items.map(item => ({
        ...item,
        detected_at: new Date(item.detected_at),
        // Add computed properties
        isRecent: Date.now() - new Date(item.detected_at).getTime() < 3600000
      })),
      pagination: response.pagination
    }
  }
})
```

## Conclusion

The Prebetter application demonstrates strong fundamentals in Nuxt 3 data fetching:

### Strengths
- ✅ Proper useFetch/\$fetch usage patterns
- ✅ Secure API proxy with token injection
- ✅ Sophisticated URL state management
- ✅ Performance-conscious auto-refresh
- ✅ Multi-level loading states
- ✅ Global 401 handling

### Areas for Improvement
- ⚠️ Missing error boundaries for graceful failures
- ⚠️ No optimistic update patterns
- ⚠️ Limited cache control strategies
- ⚠️ No request retry mechanisms
- ⚠️ Missing race condition handling
- ⚠️ No request timeout configuration

### Priority Recommendations
1. **High**: Implement error boundaries for better UX
2. **High**: Add getCachedData for cache control
3. **Medium**: Implement optimistic updates for user actions
4. **Medium**: Add retry logic with exponential backoff
5. **Low**: Consider implementing request deduplication
6. **Low**: Add request timeout configuration

The application's data fetching architecture is production-ready but would benefit from these enhancements to handle edge cases and improve user experience during error scenarios.