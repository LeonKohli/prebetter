# Vue > Nuxt > VueUse Principles Summary

## Changes Made

### 1. Replaced `useVModel` with Native Vue Computed
- **Files**: `Input.vue`, `Textarea.vue`
- **Reason**: Native Vue `computed` with getter/setter is clearer and doesn't require external dependencies for simple v-model handling
- **Before**: Used VueUse's `useVModel`
- **After**: Native `computed` with proper TypeScript typing

### 2. Fixed TypeScript Issues
- **Files**: `AlertActions.vue`, `UserActions.vue`
- **Changes**:
  - Replaced `any` types with proper union types
  - Fixed event naming to follow Vue conventions

## Justified VueUse Usage (Kept)

### Performance & Browser APIs
- **`useIntervalFn`**: Provides pause/resume functionality for auto-refresh
- **`useDocumentVisibility`**: Clean cross-browser page visibility API
- **`useNow`**: Reactive current time with proper cleanup

### Debouncing
- **`useDebounceFn`** & **`watchDebounced`**: While native solutions exist, VueUse provides:
  - Consistent API across the codebase
  - Built-in cleanup
  - TypeScript support
  - Well-tested implementation

### UI Component Pattern
- **`reactiveOmit`**: Used extensively (70+ times) in shadcn-vue components
  - Part of the UI library's established pattern
  - Provides clean prop filtering for component composition
  - Would require significant refactoring to remove

## Key Principles Applied

1. **Use Vue Native First**: For basic reactivity, use `ref`, `reactive`, `computed`
2. **Nuxt for Framework Features**: Use Nuxt composables for SSR, routing, and framework-specific needs
3. **VueUse for Complex Utilities**: Only when it provides significant value over native solutions

## Result

The codebase now better follows the Vue > Nuxt > VueUse hierarchy, using native Vue solutions where appropriate while keeping VueUse for cases where it genuinely adds value.