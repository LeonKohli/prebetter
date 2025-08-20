# Vue Native Solutions Analysis

This document analyzes where the codebase uses VueUse or Nuxt utilities when Vue native solutions would be better.

## Summary of Findings

### VueUse Usage

1. **useVModel** - Used in Input.vue and Textarea.vue for v-model handling
2. **reactiveOmit** - Used extensively in UI components (70+ files)
3. **useIntervalFn** - Used in AlertsTable.vue for auto-refresh
4. **useDocumentVisibility** - Used in AlertsTable.vue 
5. **watchDebounced** - Used in AlertsTable.vue for debouncing
6. **useDebounceFn** - Used in AlertsToolbar.vue for search debouncing
7. **useNow** - Used in DateRangePicker.vue and dateHelpers.ts
8. **useCurrentElement** - Used in CommandItem.vue

### Nuxt Composables

No excessive usage of Nuxt composables found. The codebase appears to use them appropriately (useFetch examples are in documentation only).

## Immediate Refactoring Opportunities

### 1. Replace useVModel with Native Vue

**Files affected:**
- `/home/leon/Documents/GitHub/prebetter/frontend/app/components/ui/input/Input.vue`
- `/home/leon/Documents/GitHub/prebetter/frontend/app/components/ui/textarea/Textarea.vue`

**Current pattern:**
```typescript
const modelValue = useVModel(props, 'modelValue', emits, {
  passive: true,
  defaultValue: props.defaultValue,
})
```

**Native Vue solution:**
```typescript
const modelValue = computed({
  get: () => props.modelValue ?? props.defaultValue,
  set: (value) => emits('update:modelValue', value)
})
```

### 2. Replace useDebounceFn with Native Implementation

**File affected:**
- `/home/leon/Documents/GitHub/prebetter/frontend/app/components/alerts/AlertsToolbar.vue`

**Current pattern:**
```typescript
const handleSearchFilter = useDebounceFn(updateSearchFilter, 300)
```

**Native Vue solution:**
Create a simple debounce utility or use a lightweight implementation.

### 3. Replace watchDebounced with Native watch + Debounce

**File affected:**
- `/home/leon/Documents/GitHub/prebetter/frontend/app/components/alerts/AlertsTable.vue`

**Current pattern:**
```typescript
watchDebounced(
  fetchKey,
  () => { execute() },
  { debounce: 50 }
)
```

**Native Vue solution:**
Use native `watch` with a simple debounce utility.

## Complex Refactoring Needs

### 1. reactiveOmit Usage

**Issue:** Used in 70+ UI component files, primarily in the shadcn-vue component library.

**Analysis:** This is deeply integrated into the component library pattern. While it could be replaced with native destructuring and reactive() or computed properties, the benefit is minimal since:
- It's consistently used across all UI components
- It provides a clean way to separate props for delegation
- The performance impact is negligible

**Recommendation:** Keep as-is for UI components. This is a reasonable use of VueUse for component libraries.

### 2. useIntervalFn for Auto-refresh

**File:** `/home/leon/Documents/GitHub/prebetter/frontend/app/components/alerts/AlertsTable.vue`

**Analysis:** `useIntervalFn` provides pause/resume functionality and reactive state management. While this could be replaced with `setInterval`, the VueUse version offers:
- Automatic cleanup on component unmount
- Pause/resume functionality
- Reactive state tracking

**Recommendation:** Keep as-is. This is a good use case for VueUse.

### 3. useNow for Reactive Time

**Files:**
- `/home/leon/Documents/GitHub/prebetter/frontend/app/components/DateRangePicker.vue`
- `/home/leon/Documents/GitHub/prebetter/frontend/app/utils/dateHelpers.ts`

**Analysis:** Provides a reactive current time that updates automatically. Native implementation would require:
- Manual interval setup
- Cleanup handling
- Reactive wrapper

**Recommendation:** Keep as-is. This is a legitimate use case for VueUse.

### 4. useDocumentVisibility

**File:** `/home/leon/Documents/GitHub/prebetter/frontend/app/components/alerts/AlertsTable.vue`

**Analysis:** Monitors page visibility for pausing auto-refresh. Native implementation would require:
- Event listener setup/cleanup
- Cross-browser compatibility handling

**Recommendation:** Keep as-is. This provides good cross-browser support.

## Completed Refactorings

### 1. Replaced useVModel with Native Vue Computed (✅ DONE)

**Files updated:**
- `/home/leon/Documents/GitHub/prebetter/frontend/app/components/ui/input/Input.vue`
- `/home/leon/Documents/GitHub/prebetter/frontend/app/components/ui/textarea/Textarea.vue`

**Result:** Now using native Vue computed properties for v-model handling

### 2. Created Native Debounce Utility (✅ DONE)

**New file created:**
- `/home/leon/Documents/GitHub/prebetter/frontend/app/utils/debounce.ts`

**Files updated:**
- `/home/leon/Documents/GitHub/prebetter/frontend/app/components/alerts/AlertsToolbar.vue` - Replaced useDebounceFn
- `/home/leon/Documents/GitHub/prebetter/frontend/app/components/alerts/AlertsTable.vue` - Replaced watchDebounced from VueUse

**Result:** Now using native implementation for debouncing

## Recommendations

### Immediate Actions (Simple Fixes)

1. ✅ **Replace useVModel in Input/Textarea components** - COMPLETED
2. ✅ **Create native debounce utility** - COMPLETED

### Keep As-Is (Justified Usage)

1. **reactiveOmit** - Consistent UI component pattern, minimal overhead
2. **useIntervalFn** - Provides valuable pause/resume functionality
3. **useNow** - Clean reactive time implementation
4. **useDocumentVisibility** - Good cross-browser support

### General Principles Moving Forward

1. **Prefer Vue native for simple reactivity**: Use `ref`, `reactive`, `computed` instead of VueUse utilities
2. **Use VueUse for complex utilities**: Keep for things like intervals, debouncing, browser APIs
3. **Avoid over-abstraction**: Don't use composables for simple one-liners
4. **Document why**: When using VueUse, comment why native Vue isn't sufficient

## Code Quality Impact

The current usage is mostly reasonable. The main over-engineering is in simple v-model handling where native Vue computed properties would be clearer and have less overhead. The UI component library's consistent use of `reactiveOmit` is acceptable as a pattern, though verbose.