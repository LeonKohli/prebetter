# Prebetter Frontend Developer Guide

A comprehensive guide for developers working with the Prebetter SIEM Dashboard frontend built with Nuxt 3.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication Implementation](#authentication-implementation)
3. [Common Development Tasks](#common-development-tasks)
4. [Code Examples](#code-examples)
5. [Troubleshooting Guide](#troubleshooting-guide)

## Getting Started

### Prerequisites and System Requirements

- **Node.js**: v18.0.0 or higher
- **Bun**: Latest version (required package manager)
- **Backend**: Prebetter backend API running on port 8000
- **IDE**: VS Code recommended with Vue - Official extension

### Environment Setup

1. **Clone the repository and navigate to frontend**:
```bash
cd prebetter/frontend
```

2. **Install dependencies using Bun**:
```bash
bun install
```

3. **Configure environment variables**:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Backend API URL (server-side only, not exposed to client)
API_BASE_URL=http://localhost:8000

# Session password for secure cookies (minimum 32 characters)
# Generate with: openssl rand -hex 32
NUXT_SESSION_PASSWORD=your-32-character-minimum-session-password-here
```

### Running the Development Server

```bash
bun run dev
```

The application will be available at `http://localhost:3000`

### Understanding the Architecture

The frontend follows a modern Nuxt 3 architecture:

```
frontend/
├── app/
│   ├── components/      # Reusable Vue components
│   │   └── ui/         # shadcn-vue UI components
│   ├── composables/    # Composition API composables
│   ├── layouts/        # Page layouts
│   ├── middleware/     # Route middleware
│   ├── pages/          # File-based routing
│   └── utils/          # Utility functions
├── server/
│   ├── api/           # Server API endpoints (BFF pattern)
│   └── plugins/       # Server plugins
└── public/            # Static assets
```

## Authentication Implementation

### How Sessions Work with nuxt-auth-utils

Prebetter uses `nuxt-auth-utils` for secure session management:

1. **Login Flow**:
   - User submits credentials to `/api/auth/login`
   - Server validates with backend API
   - JWT token stored securely in session (server-side only)
   - User info stored in client-accessible session data

2. **Session Structure**:
```typescript
interface UserSession {
  user: {
    id: number
    email: string
    username: string
    fullName: string
    isSuperuser: boolean
  }
  secure: {
    apiToken: string  // JWT token - server-side only
  }
  loggedInAt: string
}
```

3. **Session Configuration**:
   - 30-minute expiration (matches backend JWT)
   - Secure httpOnly cookies
   - Automatic session refresh on activity

### Adding New Protected Routes

1. **Create a protected page**:
```vue
<!-- app/pages/alerts.vue -->
<template>
  <div>
    <h1>Security Alerts</h1>
    <!-- Your content here -->
  </div>
</template>

<script setup lang="ts">
// This page requires authentication
definePageMeta({
  requiresAuth: true
})

// Access user session
const { user } = await useUserSession()
</script>
```

2. **Guest-only pages** (like login):
```vue
<script setup lang="ts">
definePageMeta({
  guestOnly: true,  // Redirects to dashboard if already logged in
  layout: false     // Optionally disable default layout
})
</script>
```

### Handling Authentication in Components

```vue
<script setup lang="ts">
// Use the session composable
const { user, loggedIn, clear } = useUserSession()

// Logout function
async function logout() {
  await clear()
  await navigateTo('/login')
}

// Conditional rendering based on auth state
const showAdminFeatures = computed(() => user.value?.isSuperuser)
</script>

<template>
  <div v-if="loggedIn">
    <p>Welcome, {{ user?.username }}!</p>
    <Button v-if="showAdminFeatures" @click="navigateToAdmin">
      Admin Panel
    </Button>
    <Button @click="logout">Logout</Button>
  </div>
</template>
```

### Testing Authentication Flows

1. **Test protected route access**:
```typescript
// tests/auth.test.ts
import { describe, it, expect } from 'vitest'

describe('Authentication', () => {
  it('redirects to login when accessing protected route', async () => {
    // Clear any existing session
    await $fetch('/api/auth/logout', { method: 'POST' })
    
    // Try to access protected route
    const response = await $fetch('/profile', { redirect: 'manual' })
    expect(response.headers.location).toBe('/login?redirect=/profile')
  })
})
```

## Common Development Tasks

### Creating New Pages with Proper Metadata

```vue
<!-- app/pages/statistics/timeline.vue -->
<template>
  <div>
    <h1 class="text-3xl font-bold mb-6">Alert Timeline</h1>
    <!-- Page content -->
  </div>
</template>

<script setup lang="ts">
// SEO metadata
useSeoMeta({
  title: 'Alert Timeline | Prebetter SIEM',
  description: 'View security alert trends over time',
})

// Page-specific configuration
definePageMeta({
  requiresAuth: true,
  middleware: 'admin-only'  // Custom middleware
})
</script>
```

### Adding API Endpoints with Authentication

1. **Create a server API route**:
```typescript
// server/api/alerts/export.get.ts
export default defineEventHandler(async (event) => {
  // Get authenticated session
  const session = await requireUserSession(event)
  
  // Access the secure API token
  const token = session.secure?.apiToken
  if (!token) {
    throw createError({
      statusCode: 401,
      statusMessage: 'Authentication required'
    })
  }
  
  // Make authenticated request to backend
  const { apiBase } = useRuntimeConfig()
  const data = await $fetch(`${apiBase}/api/v1/alerts/export`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
  
  return data
})
```

2. **Use the API proxy for backend calls**:
```vue
<script setup lang="ts">
// The catch-all proxy automatically adds authentication
const { data: alerts } = await useFetch('/api/alerts', {
  query: {
    severity: 'high',
    limit: 50
  }
})
</script>
```

### Implementing Data Tables with Filtering

```vue
<!-- app/components/AlertTable.vue -->
<template>
  <div class="space-y-4">
    <!-- Filters -->
    <div class="flex gap-4">
      <Input
        v-model="searchQuery"
        placeholder="Search alerts..."
        class="max-w-sm"
      />
      <Select v-model="severityFilter">
        <SelectTrigger class="w-[180px]">
          <SelectValue placeholder="Severity" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Severities</SelectItem>
          <SelectItem value="high">High</SelectItem>
          <SelectItem value="medium">Medium</SelectItem>
          <SelectItem value="low">Low</SelectItem>
        </SelectContent>
      </Select>
    </div>

    <!-- Table -->
    <Card>
      <CardContent class="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Alert ID</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Classification</TableHead>
              <TableHead>Timestamp</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="alert in filteredAlerts" :key="alert.id">
              <TableCell>{{ alert.id }}</TableCell>
              <TableCell>
                <Badge :variant="getSeverityVariant(alert.severity)">
                  {{ alert.severity }}
                </Badge>
              </TableCell>
              <TableCell>{{ alert.classification }}</TableCell>
              <TableCell>{{ formatDate(alert.timestamp) }}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
const searchQuery = ref('')
const severityFilter = ref('all')

// Fetch data with authentication
const { data: alerts, pending, refresh } = await useFetch('/api/alerts')

// Computed filtered results
const filteredAlerts = computed(() => {
  let results = alerts.value?.items || []
  
  // Apply severity filter
  if (severityFilter.value !== 'all') {
    results = results.filter(a => a.severity === severityFilter.value)
  }
  
  // Apply search
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    results = results.filter(a => 
      a.classification.toLowerCase().includes(query) ||
      a.id.toString().includes(query)
    )
  }
  
  return results
})

// Watch for filter changes and debounce API calls
const debouncedRefresh = useDebounceFn(refresh, 300)
watch([searchQuery, severityFilter], () => {
  debouncedRefresh()
})
</script>
```

### Using shadcn-vue Components Effectively

1. **Install new components**:
```bash
bunx shadcn-vue@latest add button card table badge
```

2. **Component usage patterns**:
```vue
<script setup lang="ts">
import { Button } from '@/components/ui/button'
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card'
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>Dashboard</CardTitle>
      <CardDescription>Monitor your security alerts</CardDescription>
    </CardHeader>
    <CardContent>
      <Button @click="handleAction" variant="default" size="lg">
        <Icon name="lucide:shield" class="mr-2 size-4" />
        View Alerts
      </Button>
    </CardContent>
  </Card>
</template>
```

## Code Examples

### Protected Page Template

```vue
<!-- app/pages/admin/users.vue -->
<template>
  <div class="container mx-auto py-6">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-3xl font-bold">User Management</h1>
      <Button @click="showCreateModal = true">
        <Icon name="lucide:plus" class="mr-2 size-4" />
        Add User
      </Button>
    </div>

    <!-- Error handling -->
    <Alert v-if="error" variant="destructive" class="mb-6">
      <AlertDescription>
        {{ error.message }}
      </AlertDescription>
    </Alert>

    <!-- Loading state -->
    <div v-if="pending" class="flex justify-center py-12">
      <Icon name="lucide:loader-2" class="size-8 animate-spin text-muted-foreground" />
    </div>

    <!-- Content -->
    <div v-else>
      <!-- Your content here -->
    </div>
  </div>
</template>

<script setup lang="ts">
// SEO
useSeoMeta({
  title: 'User Management | Prebetter Admin',
  description: 'Manage system users and permissions'
})

// Page protection
definePageMeta({
  requiresAuth: true,
  middleware: async (to, from) => {
    const { user } = await useUserSession()
    if (!user.value?.isSuperuser) {
      throw createError({
        statusCode: 403,
        statusMessage: 'Admin access required'
      })
    }
  }
})

// State
const showCreateModal = ref(false)

// Fetch data
const { data, pending, error, refresh } = await useFetch('/api/users')
</script>
```

### Authenticated API Call Patterns

```typescript
// composables/useAlerts.ts
export const useAlerts = () => {
  // Reactive filters
  const filters = reactive({
    severity: undefined as string | undefined,
    classification: undefined as string | undefined,
    startDate: undefined as string | undefined,
    endDate: undefined as string | undefined,
    page: 1,
    limit: 50
  })

  // Computed query params
  const queryParams = computed(() => {
    const params: Record<string, any> = {}
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        params[key] = value
      }
    })
    return params
  })

  // Fetch with authentication (automatic through proxy)
  const { data, pending, error, refresh } = useFetch('/api/alerts', {
    query: queryParams,
    watch: [queryParams]  // Auto-refresh on filter change
  })

  // Export alert data
  async function exportAlerts(format: 'csv' | 'json' = 'csv') {
    try {
      const blob = await $fetch(`/api/alerts/export/${format}`, {
        query: queryParams.value,
        responseType: 'blob'
      })
      
      // Download file
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `alerts-${new Date().toISOString()}.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed:', err)
      throw err
    }
  }

  return {
    alerts: computed(() => data.value?.items || []),
    total: computed(() => data.value?.total || 0),
    filters,
    pending,
    error,
    refresh,
    exportAlerts
  }
}
```

### Form with Validation Example

```vue
<!-- app/components/CreateUserForm.vue -->
<template>
  <form @submit.prevent="handleSubmit" class="space-y-4">
    <!-- Username field -->
    <div class="space-y-2">
      <Label for="username">Username</Label>
      <Input
        id="username"
        v-model="form.username"
        :class="{ 'border-destructive': errors.username }"
        @blur="validateField('username')"
      />
      <p v-if="errors.username" class="text-sm text-destructive">
        {{ errors.username }}
      </p>
    </div>

    <!-- Email field -->
    <div class="space-y-2">
      <Label for="email">Email</Label>
      <Input
        id="email"
        v-model="form.email"
        type="email"
        :class="{ 'border-destructive': errors.email }"
        @blur="validateField('email')"
      />
      <p v-if="errors.email" class="text-sm text-destructive">
        {{ errors.email }}
      </p>
    </div>

    <!-- Password field -->
    <div class="space-y-2">
      <Label for="password">Password</Label>
      <Input
        id="password"
        v-model="form.password"
        type="password"
        :class="{ 'border-destructive': errors.password }"
        @blur="validateField('password')"
      />
      <p v-if="errors.password" class="text-sm text-destructive">
        {{ errors.password }}
      </p>
    </div>

    <!-- Submit button -->
    <Button type="submit" :disabled="loading || !isValid" class="w-full">
      <Icon v-if="loading" name="lucide:loader-2" class="mr-2 size-4 animate-spin" />
      {{ loading ? 'Creating...' : 'Create User' }}
    </Button>
  </form>
</template>

<script setup lang="ts">
const emit = defineEmits<{
  success: [user: any]
  error: [error: Error]
}>()

// Form state
const form = reactive({
  username: '',
  email: '',
  password: ''
})

const errors = reactive({
  username: '',
  email: '',
  password: ''
})

const loading = ref(false)

// Validation rules
const validators = {
  username: (value: string) => {
    if (!value) return 'Username is required'
    if (value.length < 3) return 'Username must be at least 3 characters'
    if (!/^[a-zA-Z0-9_]+$/.test(value)) return 'Username can only contain letters, numbers, and underscores'
    return ''
  },
  email: (value: string) => {
    if (!value) return 'Email is required'
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return 'Invalid email format'
    return ''
  },
  password: (value: string) => {
    if (!value) return 'Password is required'
    if (value.length < 8) return 'Password must be at least 8 characters'
    return ''
  }
}

// Field validation
function validateField(field: keyof typeof form) {
  errors[field] = validators[field](form[field])
}

// Form validation
const isValid = computed(() => {
  return Object.values(errors).every(error => !error) &&
         Object.values(form).every(value => value)
})

// Submit handler
async function handleSubmit() {
  // Validate all fields
  Object.keys(form).forEach(field => {
    validateField(field as keyof typeof form)
  })

  if (!isValid.value) return

  loading.value = true
  
  try {
    const user = await $fetch('/api/users', {
      method: 'POST',
      body: form
    })
    
    emit('success', user)
    
    // Reset form
    Object.assign(form, {
      username: '',
      email: '',
      password: ''
    })
  } catch (error: any) {
    emit('error', error)
  } finally {
    loading.value = false
  }
}
</script>
```

### Data Fetching with Error Handling

```vue
<!-- app/pages/alerts/[id].vue -->
<template>
  <div class="container mx-auto py-6">
    <!-- Loading state -->
    <div v-if="pending" class="flex justify-center py-12">
      <Icon name="lucide:loader-2" class="size-8 animate-spin text-muted-foreground" />
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="mx-auto max-w-md">
      <Card>
        <CardHeader>
          <CardTitle class="text-destructive">Error Loading Alert</CardTitle>
        </CardHeader>
        <CardContent>
          <p class="mb-4">{{ error.message }}</p>
          <div class="flex gap-4">
            <Button @click="refresh" variant="outline">
              <Icon name="lucide:refresh-cw" class="mr-2 size-4" />
              Retry
            </Button>
            <Button @click="navigateTo('/alerts')">
              Back to Alerts
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Success state -->
    <div v-else-if="alert">
      <div class="mb-6 flex items-center justify-between">
        <h1 class="text-3xl font-bold">Alert Details</h1>
        <Button @click="navigateTo('/alerts')" variant="outline">
          <Icon name="lucide:arrow-left" class="mr-2 size-4" />
          Back
        </Button>
      </div>

      <!-- Alert content -->
      <Card>
        <CardHeader>
          <CardTitle>Alert #{{ alert.id }}</CardTitle>
          <CardDescription>
            Detected at {{ formatDate(alert.detectTime) }}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <!-- Alert details here -->
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
// Get route params
const route = useRoute()
const alertId = route.params.id

// SEO
useSeoMeta({
  title: () => alert.value ? `Alert #${alert.value.id} | Prebetter` : 'Loading...',
})

// Page protection
definePageMeta({
  requiresAuth: true,
  validate: async (route) => {
    // Validate ID is numeric
    return /^\d+$/.test(route.params.id as string)
  }
})

// Fetch alert with error handling
const { data: alert, pending, error, refresh } = await useFetch(`/api/alerts/${alertId}`, {
  // Handle specific error codes
  onResponseError({ response }) {
    if (response.status === 404) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Alert not found'
      })
    }
  }
})

// Utility functions
function formatDate(date: string) {
  return new Date(date).toLocaleString()
}
</script>
```

## Troubleshooting Guide

### Common Authentication Issues

1. **"User is not authenticated" errors**:
   - Check session cookie exists in browser DevTools
   - Verify `NUXT_SESSION_PASSWORD` is set correctly
   - Ensure backend is running and accessible

2. **Session expires too quickly**:
   - Check `runtimeConfig.session.maxAge` matches backend JWT expiration
   - Verify system clocks are synchronized
   - Consider implementing session refresh logic

3. **CORS errors**:
   - Backend CORS should allow frontend origin
   - Check `BACKEND_CORS_ORIGINS` in backend `.env`

### Session Debugging Tips

```typescript
// utils/debug-session.ts
export async function debugSession() {
  // Check client-side session state
  const { user, loggedIn, ready } = useUserSession()
  console.log('Session State:', {
    loggedIn: loggedIn.value,
    ready: ready.value,
    user: user.value
  })

  // Check server-side session
  try {
    const session = await $fetch('/api/debug/session')
    console.log('Server Session:', session)
  } catch (error) {
    console.error('Failed to fetch server session:', error)
  }
}

// server/api/debug/session.get.ts (development only!)
export default defineEventHandler(async (event) => {
  if (process.env.NODE_ENV !== 'development') {
    throw createError({ statusCode: 404 })
  }
  
  const session = await getUserSession(event)
  return {
    hasSession: !!session,
    hasUser: !!session.user,
    hasToken: !!session.secure?.apiToken,
    sessionAge: session.loggedInAt 
      ? Date.now() - new Date(session.loggedInAt).getTime() 
      : null
  }
})
```

### Performance Optimization

1. **Lazy load heavy components**:
```vue
<script setup lang="ts">
const AlertChart = defineAsyncComponent(() => 
  import('@/components/AlertChart.vue')
)
</script>
```

2. **Cache reference data**:
```typescript
// composables/useReferenceData.ts
export const useReferenceData = () => {
  // Use useState for cross-component caching
  const severities = useState('ref:severities', () => null)
  const classifications = useState('ref:classifications', () => null)

  async function loadReferenceData() {
    if (!severities.value) {
      const [sev, cls] = await Promise.all([
        $fetch('/api/reference/severities'),
        $fetch('/api/reference/classifications')
      ])
      severities.value = sev
      classifications.value = cls
    }
  }

  return {
    severities: readonly(severities),
    classifications: readonly(classifications),
    loadReferenceData
  }
}
```

3. **Implement virtual scrolling for large lists**:
```vue
<script setup lang="ts">
import { VirtualList } from '@tanstack/vue-virtual'

const { data: alerts } = await useFetch('/api/alerts', {
  query: { limit: 1000 }
})

const virtualizer = useVirtualizer({
  count: alerts.value?.items.length || 0,
  getScrollElement: () => parentRef.value,
  estimateSize: () => 50,
  overscan: 5
})
</script>
```

### Deployment Considerations

1. **Environment Variables**:
   - Never commit `.env` files
   - Use proper secrets management in production
   - Different API URLs for staging/production

2. **Build optimization**:
```bash
# Production build
bun run build

# Analyze bundle size
bunx nuxi analyze
```

3. **Security headers** (add to `nuxt.config.ts`):
```typescript
export default defineNuxtConfig({
  nitro: {
    experimental: {
      securityHeaders: {
        contentSecurityPolicy: {
          'img-src': ["'self'", 'data:', 'https:'],
          'script-src': ["'self'", "'nonce-{{nonce}}'"]
        },
        crossOriginEmbedderPolicy: 'require-corp',
        crossOriginOpenerPolicy: 'same-origin',
        crossOriginResourcePolicy: 'same-origin',
        originAgentCluster: '?1',
        referrerPolicy: 'no-referrer-when-downgrade',
        strictTransportSecurity: {
          maxAge: 31536000,
          includeSubdomains: true
        },
        xContentTypeOptions: 'nosniff',
        xFrameOptions: 'DENY',
        xXSSProtection: '0'
      }
    }
  }
})
```

4. **Production checklist**:
   - [ ] Generate strong `NUXT_SESSION_PASSWORD` (32+ chars)
   - [ ] Configure proper API_BASE_URL
   - [ ] Enable HTTPS
   - [ ] Set up monitoring and error tracking
   - [ ] Configure rate limiting
   - [ ] Test session timeout handling
   - [ ] Verify CORS settings
   - [ ] Review and minimize bundle size

## Additional Resources

- [Nuxt 3 Documentation](https://nuxt.com)
- [nuxt-auth-utils Documentation](https://github.com/Atinux/nuxt-auth-utils)
- [shadcn-vue Components](https://www.shadcn-vue.com)
- [Vue 3 Composition API](https://vuejs.org/guide/extras/composition-api-faq.html)
- [Tailwind CSS v4 Docs](https://tailwindcss.com)

## Contributing

When contributing to this project:

1. Follow existing code patterns and conventions
2. Use Composition API with TypeScript
3. Ensure all pages have proper SEO metadata
4. Add appropriate error handling
5. Test authentication flows thoroughly
6. Update this guide with new patterns or examples

Happy coding! 🚀