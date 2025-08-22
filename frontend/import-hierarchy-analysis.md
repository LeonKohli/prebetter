# Import Hierarchy Analysis

## Executive Summary

After analyzing the entire codebase, I found that the import hierarchy is generally well-structured but has some inconsistencies. The main issues are:

1. **Mixed ordering patterns** - Some files follow proper hierarchy, others don't
2. **Missing grouping** - Imports aren't consistently grouped with blank lines
3. **Type imports** - Some files mix type imports with regular imports
4. **VueUse placement** - Inconsistent placement of VueUse imports relative to other libraries

## Current State Analysis

### Common Patterns Found

1. **UI Components** (e.g., Button.vue, Input.vue):
   - Often start with Vue type imports
   - Then external UI libraries (reka-ui)
   - Then internal utilities
   - Generally follow correct pattern but lack grouping

2. **Feature Components** (e.g., AlertsTable.vue):
   - Mix external libraries without clear ordering
   - VueUse imports often mixed with other external libs
   - Missing Vue core imports (auto-imported by Nuxt)

3. **Composables**:
   - Start with Vue imports (good)
   - Mix external and internal imports without clear separation

### Files Requiring Fixes

The following files have incorrect import ordering:

1. **`/app/components/alerts/AlertsTable.vue`**
   - External library imports before VueUse
   - No clear grouping

2. **`/app/components/DateRangePicker.vue`**
   - Type imports mixed with regular imports
   - External library imports not grouped

3. **`/app/components/ui/button/Button.vue`**
   - Type imports should be first
   - Missing grouping

4. **`/app/components/ui/input/Input.vue`**
   - Correct order but missing grouping

5. **`/app/components/alerts/AlertsToolbar.vue`**
   - External libraries before VueUse
   - No grouping

6. **`/app/components/profile/ProfileEditDialog.vue`**
   - External validation library before Nuxt types
   - No grouping

## Recommended Import Order

```typescript
// 1. Vue core imports (if not auto-imported)
import { ref, computed, watch } from 'vue'
import type { Ref, ComputedRef } from 'vue'

// 2. Nuxt imports
import { useRouter, useRoute } from '#app'
import type { NuxtError } from '#app'

// 3. VueUse imports
import { useVModel, useIntervalFn } from '@vueuse/core'

// 4. External library imports
import { z } from 'zod'
import { clsx } from 'clsx'
import type { ColumnDef } from '@tanstack/vue-table'

// 5. Internal imports (utils, types, components)
import { cn } from '@/utils/utils'
import type { User } from '@/types/user'
import Button from '@/components/ui/button/Button.vue'
```

## Implementation Plan

1. Fix files with incorrect VueUse placement
2. Add proper grouping with blank lines
3. Separate type imports where appropriate
4. Ensure consistent ordering across all files

## Circular Dependencies

No circular dependencies were detected during the analysis.

## Import Aliases

The codebase correctly uses:
- `@/` for absolute imports from the app directory
- `#app` for Nuxt auto-imports
- `#auth-utils` for auth module imports
- `~/` occasionally (should standardize to `@/`)