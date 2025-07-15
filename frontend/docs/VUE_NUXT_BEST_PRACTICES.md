# Vue & Nuxt Best Practices Guide

This document outlines best practices for Vue 3 and Nuxt 3 development, focusing on declarative, reactive patterns that leverage the framework's strengths.

## Table of Contents
1. [Core Principles](#core-principles)
2. [Declarative vs Imperative Patterns](#declarative-vs-imperative-patterns)
3. [Common Antipatterns & Solutions](#common-antipatterns--solutions)
4. [Practical Examples](#practical-examples)
5. [Performance Optimizations](#performance-optimizations)

## Core Principles

### 1. **Embrace Reactivity**
- Use computed properties over watchers when possible
- Leverage Vue's reactivity system for automatic updates
- Avoid manual state synchronization

### 2. **Declarative Over Imperative**
- Define what the UI should look like based on state
- Let Vue handle the "how" of updates
- Minimize side effects in components

### 3. **Composition Over Complexity**
- Use composables for reusable logic
- Keep components focused and single-purpose
- Extract complex logic into dedicated functions

## Declarative vs Imperative Patterns

### ❌ Imperative (Avoid)
```typescript
// Multiple refs with manual synchronization
const isLoading = ref(false)
const hasError = ref(false)
const errorMessage = ref('')

watch(someValue, async (newValue) => {
  isLoading.value = true
  hasError.value = false
  try {
    const result = await fetchData(newValue)
    // manual updates...
  } catch (error) {
    hasError.value = true
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
})
```

### ✅ Declarative (Prefer)
```typescript
// Let useFetch handle all state management
const { data, error, pending } = await useFetch(() => `/api/data/${someValue.value}`)

// Derive states from the source of truth
const hasError = computed(() => !!error.value)
const errorMessage = computed(() => error.value?.message || '')
```

## Common Antipatterns & Solutions

### 1. **Multiple Watchers Instead of Computed Properties**

#### ❌ Antipattern
```typescript
const firstName = ref('')
const lastName = ref('')
const fullName = ref('')

watch(firstName, () => {
  fullName.value = `${firstName.value} ${lastName.value}`
})

watch(lastName, () => {
  fullName.value = `${firstName.value} ${lastName.value}`
})
```

#### ✅ Solution
```typescript
const firstName = ref('')
const lastName = ref('')
const fullName = computed(() => `${firstName.value} ${lastName.value}`)
```

### 2. **Manual Timer Management**

#### ❌ Antipattern
```typescript
const timer = ref<NodeJS.Timeout | null>(null)

const startTimer = () => {
  stopTimer()
  timer.value = setInterval(() => {
    // do something
  }, 1000)
}

const stopTimer = () => {
  if (timer.value) {
    clearInterval(timer.value)
    timer.value = null
  }
}

onUnmounted(() => stopTimer())
```

#### ✅ Solution
```typescript
import { useIntervalFn } from '@vueuse/core'

const { pause, resume, isActive } = useIntervalFn(() => {
  // do something
}, 1000)
```

### 3. **Separate Refs for Related State**

#### ❌ Antipattern
```typescript
const username = ref('')
const password = ref('')
const isLoading = ref(false)
const errors = ref<string[]>([])
```

#### ✅ Solution
```typescript
const formState = reactive({
  username: '',
  password: '',
  isLoading: false,
  errors: [] as string[]
})

// Or with a composable
const { formState, submit, reset } = useLoginForm()
```

### 4. **Complex Column Visibility Management**

#### ❌ Antipattern (from AlertsTable.vue)
```typescript
const columnRefs: Record<string, Ref<Checked>> = {}

const initializeColumnRefs = () => {
  for (const colId of allColumns) {
    columnRefs[colId] = ref<Checked>(true)
    
    watch(columnRefs[colId], (visible) => {
      const currentState = columnVisibility.value as any || {}
      columnVisibility.value = { ...currentState, [colId]: visible }
    })
  }
}
```

#### ✅ Solution
```typescript
const columnVisibility = computed(() => {
  return allColumns.reduce((acc, colId) => ({
    ...acc,
    [colId]: urlState.hiddenColumns.value?.includes(colId) !== true
  }), {})
})

const toggleColumn = (colId: string) => {
  const hidden = [...urlState.hiddenColumns.value]
  const index = hidden.indexOf(colId)
  
  if (index > -1) {
    hidden.splice(index, 1)
  } else {
    hidden.push(colId)
  }
  
  urlState.hiddenColumns.value = hidden
}
```

### 5. **DOM Manipulation**

#### ❌ Antipattern
```typescript
if (process.client) {
  document.documentElement.dataset.authReady = 'false'
}

watch(ready, (val) => {
  if (process.client && val) {
    document.documentElement.dataset.authReady = 'true'
  }
})
```

#### ✅ Solution
```vue
<template>
  <html :data-auth-ready="ready">
    <!-- content -->
  </html>
</template>
```

### 6. **Repetitive URL Parameter Handling**

#### ❌ Antipattern
```typescript
const view = computed({
  get: () => viewParam.value,
  set: (value) => {
    if (value === defaults.view) {
      viewParam.value = undefined
    } else {
      viewParam.value = value
    }
  }
})

const page = computed({
  get: () => pageParam.value,
  set: (value) => {
    if (value <= 1) {
      pageParam.value = undefined
    } else {
      pageParam.value = value
    }
  }
})
```

#### ✅ Solution
```typescript
const createUrlParam = <T>(
  param: Ref<T>, 
  defaultValue: T,
  clearCondition?: (value: T) => boolean
) => {
  return computed({
    get: () => param.value,
    set: (value) => {
      const shouldClear = clearCondition 
        ? clearCondition(value) 
        : value === defaultValue
      
      param.value = shouldClear ? undefined as any : value
    }
  })
}

const view = createUrlParam(viewParam, defaults.view)
const page = createUrlParam(pageParam, 1, (value) => value <= 1)
```

## Practical Examples

### DateRangePicker Refactor

Our DateRangePicker component is a perfect example of moving from imperative to declarative:

#### Before (Imperative)
- Multiple refs tracking state (`activePresetLabel`, `isSelectingPreset`)
- Complex watchers managing race conditions
- Manual state synchronization
- 60+ lines of state management code

#### After (Declarative)
- Single computed property deriving active preset
- Best-match scoring algorithm
- No watchers or manual state tracking
- ~40 lines of clean, reactive code

```typescript
// Pure computed property - no side effects
const activePreset = computed(() => {
  if (!props.modelValue?.from || !props.modelValue?.to) {
    return null
  }
  
  // Best-match scoring algorithm
  let bestMatch = null
  let bestScore = Infinity
  
  for (const preset of quickPresets) {
    // Calculate match score...
    if (score < bestScore) {
      bestScore = score
      bestMatch = preset
    }
  }
  
  return bestMatch
})

// Derived from activePreset
const activePresetLabel = computed(() => activePreset.value?.label || null)
```

## Performance Optimizations

### 1. **Use Lazy Loading for Non-Critical Data**
```typescript
// Don't block navigation
const { data } = await useLazyFetch('/api/non-critical-data')
```

### 2. **Optimize Reactive Depth**
```typescript
// For large objects where deep reactivity isn't needed
const largeData = useState('data', () => shallowRef(bigObject))

// Or in useFetch
const { data } = await useFetch('/api/large-dataset', { deep: false })
```

### 3. **Conditional Fetching**
```typescript
const { data } = await useLazyFetch('/api/admin-data', {
  immediate: computed(() => !!user.value?.isAdmin)
})
```

### 4. **Smart Key Management**
```typescript
// Dynamic keys for cache invalidation
const { data } = await useAsyncData(
  () => `user-${userId.value}`,
  () => fetchUser(userId.value)
)
```

## Best Practices Summary

1. **Prefer computed over watch** - Computed properties are cached and only re-evaluate when dependencies change
2. **Use reactive/ref wisely** - Group related state, use shallowRef for performance
3. **Leverage VueUse** - Don't reinvent common patterns (intervals, storage, etc.)
4. **Think declaratively** - Describe the desired state, not the steps to get there
5. **Minimize side effects** - Keep components predictable and testable
6. **Use TypeScript** - Type safety prevents many runtime errors
7. **Extract complex logic** - Create composables for reusable functionality
8. **Optimize reactivity** - Use `deep: false` for large datasets
9. **Handle loading states properly** - Use status instead of just pending
10. **Keep components focused** - Single responsibility principle

## Resources

- [Vue 3 Reactivity Documentation](https://vuejs.org/guide/essentials/reactivity-fundamentals.html)
- [Nuxt 3 Composables](https://nuxt.com/docs/guide/directory-structure/composables)
- [VueUse Collection](https://vueuse.org/)
- [Vue Composition API Best Practices](https://vuejs.org/guide/reusability/composables.html#best-practices)

---

*Remember: The goal is to write code that clearly expresses intent while letting Vue handle the implementation details. When in doubt, choose the more declarative approach.*