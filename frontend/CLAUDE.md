# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Prebetter frontend.

**Note**: For overall project architecture and backend API details, see the [root CLAUDE.md](../CLAUDE.md).

## Prebetter Frontend Overview

Nuxt 3 SSR application providing a modern SIEM dashboard with secure session-based authentication.

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
- **Framework**: Nuxt 3.17 with Vue 3 (Composition API)
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
└── nuxt.config.ts           # Nuxt configuration
```

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

### Component Development
```vue
<script setup lang="ts">
// TypeScript always enabled
definePageMeta({
  requiresAuth: true  // For protected pages
})

// All Vue/Nuxt functions auto-imported
const { user, loggedIn } = useUserSession()
const { data, error, pending } = await useFetch('/api/alerts')

// Refs are typed automatically
const searchQuery = ref('')  // Inferred as Ref<string>
</script>
```

### Error Handling
```typescript
// Client-side errors
throw createError('Something went wrong')

// Server-side errors with status
throw createError({ 
  statusCode: 404, 
  statusMessage: 'Resource not found' 
})
```

### State Management
```typescript
// Use built-in useState for shared state
const alerts = useState('alerts', () => [])

// For complex state, create composables
export const useAlertFilters = () => {
  const severity = useState('filter-severity', () => '')
  const dateRange = useState('filter-dateRange', () => null)
  
  return { severity, dateRange }
}
```

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
<!-- app/components/AlertCard.vue -->
<template>
  <Card>
    <CardHeader>
      <CardTitle>{{ alert.title }}</CardTitle>
    </CardHeader>
    <CardContent>
      {{ alert.message }}
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
interface Props {
  alert: {
    title: string
    message: string
  }
}

defineProps<Props>()
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