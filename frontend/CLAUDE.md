# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Prebetter frontend.

**Note**: For overall project architecture and backend API details, see the [root CLAUDE.md](../CLAUDE.md).

## Prebetter Frontend Overview

Nuxt 4 SSR application providing a modern SIEM dashboard with secure session-based authentication.

## Quick Reference

```bash
# Start development server
bun run dev         # Runs on port 3000 (or 3001 if occupied)

# Type checking and building
bun run typecheck   # Check TypeScript types
bun run build       # Build for production
bun run preview     # Preview production build

# Add UI components
bunx shadcn-vue@latest add <component-name>
```

## Tech Stack & Modules

**Core:**
- **Framework**: Nuxt 4 with Vue 3 (Composition API)
- **Package Manager**: Bun (required - do not use npm/yarn/pnpm)
- **TypeScript**: Full type safety with vue-tsc

**UI & Styling:**
- **Components**: shadcn-vue (Button, Card, Checkbox, Dropdown, Input, Tabs, Textarea, Tooltip)
- **Styling**: Tailwind CSS v4 with OKLCH color system
- **Icons**: @nuxt/icon with Lucide icons
- **Theme**: Dark/light mode via @nuxtjs/color-mode

**Authentication & State:**
- **Sessions**: nuxt-auth-utils (secure server-side sessions)
- **State**: Built-in useState for reactive state management

## Authentication Architecture

**Session-Based with Server-Side JWT Storage:**

1. **Login Flow**: 
   - User submits credentials to `/api/auth/login`
   - Frontend proxies to backend `/api/v1/auth/token`
   - JWT stored in secure server-side session only
   - Session cookie (httpOnly) sent to browser

2. **API Proxy Pattern**:
   - All API calls go through `/server/api/[...].ts`
   - Server automatically injects JWT token
   - Client never sees or handles tokens

3. **Session Configuration**:
   - 30-minute expiration (matches backend JWT)
   - Encrypted with `NUXT_SESSION_PASSWORD`
   - Uses `useUserSession()` composable

4. **Route Protection**:
   ```typescript
   // In pages that require auth
   definePageMeta({
     requiresAuth: true
   })
   
   // For guest-only pages (like login)
   definePageMeta({
     guestOnly: true
   })
   ```

## Project Structure

```
frontend/
├── app/                        # Nuxt 4 app directory
│   ├── assets/css/            # Global styles
│   ├── components/            # Vue components
│   │   ├── ui/               # shadcn-vue components
│   │   ├── Navbar.vue        # App navigation
│   │   └── ColorModeToggle.vue
│   ├── composables/           # Auto-imported composables (empty - add as needed)
│   ├── layouts/              # Layout templates
│   ├── middleware/           # Route middleware
│   │   └── auth.global.ts    # Global auth checks
│   ├── pages/                # File-based routing
│   │   ├── index.vue        # Dashboard (protected)
│   │   ├── login.vue        # Login page (guest only)
│   │   └── profile.vue      # User profile (protected)
│   └── utils/               # Utility functions
├── server/                    # Nitro server directory
│   └── api/                 # Server API routes
│       ├── [...].ts         # API proxy with auth
│       └── auth/            # Auth endpoints
├── shared/                    # Shared code between client/server
│   └── types/               # TypeScript type declarations
│       └── auth.d.ts        # Auth module augmentation
└── nuxt.config.ts           # Nuxt configuration
```

## Nuxt 4 TypeScript Configuration

**Nuxt 4 uses split TypeScript configurations for better type safety:**

1. **Project References Structure**:
   ```json
   // tsconfig.json
   {
     "files": [],
     "references": [
       { "path": "./.nuxt/tsconfig.app.json" },
       { "path": "./.nuxt/tsconfig.server.json" },
       { "path": "./.nuxt/tsconfig.shared.json" },
       { "path": "./.nuxt/tsconfig.node.json" }
     ]
   }
   ```

2. **Shared Types via `shared/types/`**:
   - Place type declarations in `shared/types/` for auto-import
   - Files here are available in both client and server contexts
   - Example: `shared/types/auth.d.ts` for auth module augmentation
   - No manual imports or references needed - Nuxt handles it

3. **Type Checking**:
   ```bash
   bun run typecheck  # Uses vue-tsc -b --noEmit for project references
   ```

4. **Benefits**:
   - Better type safety with context-specific checking
   - Improved IDE experience with proper IntelliSense
   - Server code won't suggest client-side APIs and vice versa
   - Faster TypeScript performance with scoped configurations

## Data Fetching Patterns

**Current Implementation:**
```typescript
// All API calls use the proxy - NO direct backend calls
const { data, error, pending } = await useFetch('/api/users')  // Auto-proxied to backend

// Authentication is automatic via session
const { user, loggedIn } = useUserSession()

// Protected API calls work automatically
const { data } = await useFetch('/api/alerts')  // Token injected server-side
```

**Important**: Never call backend directly. Always use `/api/*` routes.

## UI Development

### Styling Rules

**Color System (OKLCH-based):**
```css
/* Use these Tailwind classes - NO arbitrary colors */
bg-background / text-foreground      /* Main background/text */
bg-card / text-card-foreground       /* Card surfaces */
bg-primary / text-primary-foreground /* Primary actions */
bg-muted / text-muted-foreground    /* Subtle content */
bg-destructive                      /* Errors/warnings */
border-border                       /* All borders */
ring-ring                          /* Focus rings */
```

**Best Practices:**
- ✅ Use inline Tailwind classes
- ❌ NO @apply directives in CSS
- ❌ NO arbitrary color values like `bg-blue-500`
- ✅ Dark/light mode handled automatically

### Icons
```vue
<!-- Always use icons via @nuxt/icon -->
<Icon name="mdi:alert-circle" class="size-4" />
<Icon name="lucide:shield" class="size-5" />
```

## Environment Configuration

**Required** in `.env`:
```env
# Session encryption key (minimum 32 characters)
NUXT_SESSION_PASSWORD=your-very-secure-password-here-minimum-32-chars
```

**In `nuxt.config.ts`:**
- Session timeout: 30 minutes (matches backend)
- API base URL: `http://localhost:8000`
- Modules configured: auth, icons, color mode, SEO

## Code Patterns & Best Practices

### Core Vue/Nuxt Development Principles

**Follow these principles for all frontend development:**

1. **Declarative Over Imperative** - Describe what the UI should be, not how to update it
2. **Embrace Reactivity** - Use computed properties and let Vue handle updates automatically
3. **Composition Over Complexity** - Keep components focused, extract logic into composables
4. **Leverage VueUse** - Don't reinvent common patterns (intervals, timeouts, visibility, etc.)
5. **Group Related State** - Use reactive objects for related data instead of multiple refs
6. **Minimize Side Effects** - Keep components predictable and testable
7. **Think in Terms of Data Flow** - Let data drive the UI, not manual DOM updates

### Event Naming Conventions

**Follow Vue 3 best practices for consistent event naming:**

1. **In emit definitions** - Use camelCase:
   ```typescript
   const emit = defineEmits<{
     updateSuccess: [user: User]
     resetPassword: []
     deleteItem: [id: string]
   }>()
   ```

2. **In templates** - Use kebab-case:
   ```vue
   <Component 
     @update-success="handleUpdate"
     @reset-password="handleReset"
     @delete-item="handleDelete"
   />
   ```

3. **When emitting** - Use camelCase (matches definition):
   ```typescript
   emit('updateSuccess', userData)
   emit('resetPassword')
   ```

**Note**: Vue automatically converts between camelCase (in code) and kebab-case (in templates).

### Vue > Nuxt > VueUse Usage Hierarchy

**Follow this principle when choosing solutions:**

1. **Vue Native First** - Use Vue's built-in features:
   - `ref`, `reactive`, `computed` for reactivity
   - `watch`, `watchEffect` for side effects
   - `provide`/`inject` for dependency injection
   - Native `v-model` with computed getters/setters

2. **Nuxt Features Second** - For framework-specific needs:
   - `useFetch`, `useAsyncData` for data fetching
   - `useState` for SSR-friendly global state
   - `navigateTo` for navigation
   - Auto-imports and file-based routing

3. **VueUse Last** - Only when it adds significant value:
   - ✅ Complex utilities: `useIntervalFn`, `useDebounceFn`
   - ✅ Browser APIs: `useDocumentVisibility`, `useLocalStorage`
   - ✅ Performance helpers: `useThrottleFn`, `useRefHistory`
   - ❌ Avoid for simple reactivity that Vue handles natively

**Example:**
```typescript
// ❌ Don't use VueUse for simple v-model
import { useVModel } from '@vueuse/core'
const model = useVModel(props, 'modelValue', emit)

// ✅ Use native Vue computed
const model = computed({
  get: () => props.modelValue,
  set: (value) => emit('updateModelValue', value)
})
```

### Essential Resources to Use

**Always consult these resources when developing:**

1. **Context7** - Your primary documentation source for ALL libraries:
   - Use `mcp__context7__resolve-library-id` to find any library
   - Use `mcp__context7__get-library-docs` to get specific documentation
   - Works for: Vue, Nuxt, VueUse, TanStack, Tailwind, TypeScript, and more
   - Always check for best practices, patterns, and examples

2. **Common Libraries to Check via Context7:**
   - **VueUse** - Utilities for Vue (timers, browser APIs, state, sensors)
   - **TanStack Table** - For table functionality
   - **Tailwind CSS** - For styling patterns and utilities
   - **Reka UI** - For UI component patterns
   - **TypeScript** - For type utilities and patterns

**Example workflow:**
```typescript
// Before implementing ANY feature:
// 1. Search Context7 for relevant libraries: "tanstack table sorting"
// 2. Get documentation for the specific topic
// 3. Use the library's solution instead of custom implementation
// 4. Follow the documented patterns and best practices
```

### Common Patterns to Follow

- Prefer `computed` over `watch` for derived state
- Use `reactive` for forms and complex state objects
- Use `shallowRef` for large objects when deep reactivity isn't needed
- Always use TypeScript for type safety
- Extract reusable logic into composables
- Create factory functions to reduce repetitive patterns

### Performance Considerations

- Use `lazy: true` for non-critical data fetches
- Add `deep: false` to `useFetch` for large datasets
- Implement conditional fetching with computed properties
- Use proper key management for caching

## Security Implementation

**Current Security Features:**
- ✅ JWT tokens stored server-side only
- ✅ Session cookies are httpOnly and encrypted
- ✅ Automatic CSRF protection via session cookies
- ✅ API proxy prevents direct backend exposure

**Security Best Practices:**
- Never store tokens in localStorage/sessionStorage
- All API calls must go through server proxy
- Validate and sanitize user inputs
- Use server-side validation for critical operations

## Performance Optimization

**Currently Implemented:**
- SSR for initial page load
- Auto-imports reduce bundle size
- Tailwind CSS tree-shaking

**Recommended Optimizations:**
- Add `lazy: true` to non-critical data fetches
- Implement virtual scrolling for large lists
- Use `useState` to cache reference data
- Use `deep: false` for large datasets
- Implement proper loading states with `status` instead of just `pending`

## Testing

**Current Status:**
- Vitest configured but no tests implemented
- Type checking via `bun run typecheck`

**Testing Commands:**
```bash
bun run test        # Run tests (when implemented)
bun run typecheck   # Check TypeScript types
```

## Common Development Tasks

### Adding a Protected Page
```vue
<!-- app/pages/newpage.vue -->
<template>
  <div>Protected content here</div>
</template>

<script setup lang="ts">
definePageMeta({
  requiresAuth: true
})

const { user } = useUserSession()
const { data } = await useFetch('/api/protected-data')
</script>
```

### Creating a Reusable Component
```vue
<script setup lang="ts">
// Define props with TypeScript
interface Props {
  data: YourDataType
}

const props = defineProps<Props>()

// Use computed properties for derived state
const displayValue = computed(() => 
  // Transform data declaratively
  props.data.someTransformation()
)

// Group related state
const uiState = reactive({
  isExpanded: false,
  selectedItem: null
})
</script>
```

### Handling Forms
```vue
<script setup lang="ts">
const form = reactive({
  email: '',
  message: ''
})

const { $fetch } = useNuxtApp()

async function submitForm() {
  try {
    await $fetch('/api/contact', {
      method: 'POST', 
      body: form
    })
    // Success handling
  } catch (error) {
    // Error handling
  }
}
</script>
```

## Important Conventions

- **Package Manager**: Always use `bun` (not npm/yarn/pnpm)
- **Node Version**: 18+ required
- **Auto-imports**: Never manually import Vue/Nuxt functions
- **API Calls**: Always use proxy routes (`/api/*`)
- **Type Safety**: TypeScript is enforced throughout
- **Git Commits**: Never include "Co-Authored-By: Claude"

## Critical: Dynamic URL Switching with useFetch

**When switching between different API endpoints dynamically (e.g., `/api/alerts` ↔ `/api/alerts/groups`):**
1. Use a comprehensive key that includes ALL reactive state to prevent NS_BINDING_ABORTED errors
2. Set `immediate: false` and `watch: false` in useFetch options, then manually control with `watchDebounced`
3. This approach prevents request cancellation while maintaining reactivity and follows Nuxt 4 patterns

  ## Key Development Philosophy

  **When developing Vue/Nuxt components:**
  - Write declarative code that describes the desired state
  - Let Vue's reactivity handle updates automatically
  - Use composables and computed properties extensively
  - Avoid manual DOM manipulation and imperative patterns
  - Group related state in reactive objects
  - **ALWAYS check VueUse and Context7 before implementing utilities**

  **Development Process:**
  1. Check if VueUse has a utility for your need
  2. Use Context7 to find Vue/Nuxt best practices
  3. Follow established patterns from the documentation
  4. Only create custom solutions when absolutely necessary

  **Remember**: The goal is clean, maintainable code that leverages existing solutions rather than reinventing them.