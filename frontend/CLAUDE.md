# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Note**: For overall project guidance and backend integration details, see the [root CLAUDE.md](../CLAUDE.md).

## Project Overview

**Prebetter Frontend** is a SIEM/IDS (Security Information and Event Management / Intrusion Detection System) dashboard built with Nuxt 3. It interfaces with the Prebetter backend API to display security alerts, system heartbeats, and statistics from a Prelude SIEM system.

## Tech Stack

- **Framework**: Nuxt 3 with Vue 3 (Composition API only)
- **UI Components**: shadcn-vue (Reka UI)
- **Styling**: Tailwind CSS v4 with CSS variables
- **Package Manager**: Bun (required - do not use npm/yarn/pnpm)
- **Type Checking**: TypeScript with vue-tsc
- **Utilities**: VueUse for composition utilities

## Development Commands

```bash
# Development
bun run dev          # Start development server (runs on port 3000)

# Type checking
bun run typecheck    # Run type checking with nuxi typecheck

# Building
bun run build        # Build for production
bun run preview      # Preview production build
bun run generate     # Generate static site

# Testing
bun run test         # Run tests with Vitest

# Adding UI components
bunx shadcn-vue@latest add <component-name>
```

## Backend API Integration

The Prebetter backend API is located at `/home/leon/Documents/GitHub/prebetter/backend` and provides:

### Base URL: `http://localhost:8000/api/v1`

### Authentication
- JWT Bearer token authentication
- Login endpoint: `POST /api/v1/auth/token`
- Use `useFetch` with auth headers for authenticated requests

### Key API Endpoints
- **Alerts**: `/alerts/` - Security alerts with extensive filtering
- **Statistics**: `/statistics/timeline`, `/statistics/summary`
- **Heartbeats**: `/heartbeats/status`, `/heartbeats/tree`
- **Reference Data**: `/reference/classifications`, `/reference/severities`
- **Export**: `/export/alerts/{format}` (CSV support)

## Architecture Guidelines

### Directory Structure
- `app/components/` - Vue components (PascalCase naming)
- `app/components/ui/` - shadcn-vue UI components
- `app/pages/` - File-based routing (camelCase naming)
- `app/composables/` - Reusable composition functions (use[Name] pattern)
- `app/layouts/` - Layout templates
- `app/utils/` - Utility functions
- `server/api/` - Server API endpoints (for BFF pattern if needed)

### State Management & Data Fetching

1. **Authentication State**: Create `useAuth` composable for JWT token management
2. **API Composables**: Create dedicated composables for each API domain:
   - `useAlerts()` - Alert fetching and filtering
   - `useStatistics()` - Dashboard statistics
   - `useHeartbeats()` - System health monitoring
   - `useReference()` - Reference data caching

3. **Data Fetching Patterns**:
   ```typescript
   // For SSR-optimized requests
   const { data, error, pending } = await useFetch('/api/v1/alerts', {
     baseURL: 'http://localhost:8000',
     headers: {
       Authorization: `Bearer ${token.value}`
     }
   })
   ```

## Component Development

### UI Components
- Use existing shadcn-vue components from `app/components/ui/`
- Available components include: Button, Card, Checkbox, Input, Dropdown Menu, Tabs, Textarea, Tooltip
- Add new shadcn components as needed: `bunx shadcn-vue@latest add <component-name>`

### Styling Guidelines
- Use inline Tailwind classes only - no @apply directives
- **IMPORTANT**: Always use predefined color variables from `app/assets/css/main.css`:
  - `bg-background`, `text-foreground` for main content
  - `bg-card`, `text-card-foreground` for cards
  - `bg-primary`, `text-primary-foreground` for primary actions
  - `bg-secondary`, `text-secondary-foreground` for secondary elements
  - `bg-muted`, `text-muted-foreground` for muted/subtle content
  - `bg-destructive`, `text-destructive-foreground` for errors/warnings
  - `border-border` for borders
  - `ring-ring` for focus states
- Never use arbitrary color values or Tailwind's default colors
- The color system uses OKLCH color space and automatically adapts to dark/light modes

### Icons
Use `<Icon>` component from @nuxt/icon with Lucide icons:
```vue
<Icon name="lucide:shield-alert" class="size-5" />
```

## Prebetter-Specific Features

### Alert Dashboard
- Display alerts in a data table with sorting and filtering
- Implement faceted filters for severity, classification, analyzer
- Show alert timeline charts using chart components
- Group alerts by source/target IPs

### System Health Monitoring
- Display heartbeat status in a tree view
- Show online/offline status for hosts and agents
- Implement real-time updates using polling or WebSocket

### Statistics & Analytics
- Create dashboard cards for summary statistics
- Implement timeline charts (hourly, daily, weekly, monthly)
- Export functionality for alerts (CSV format)

### Filter System
Create a comprehensive filter system supporting:
- Date range selection
- Severity levels (High, Medium, Low, Info)
- Classifications
- IP address filtering (source/target)
- Analyzer selection
- Pagination with configurable page size

## Code Style Requirements

1. **Always use Composition API with TypeScript**
2. **No manual imports for Vue/Nuxt functions** - They are auto-imported
3. **Error Handling**:
   - Client: `throw createError('Error message')`
   - Server: `throw createError({ statusCode: 404, statusMessage: 'Not found' })`
4. **TypeScript**: Use interfaces over types for better extendability

## Performance Considerations

- Implement pagination for large datasets
- Use lazy loading for below-fold content
- Cache reference data (classifications, severities) using `useState`
- Debounce search inputs and filters
- Consider virtual scrolling for large alert tables

## Security Considerations

- Store JWT tokens securely (consider using httpOnly cookies)
- Implement token refresh logic
- Validate all user inputs
- Sanitize displayed alert data to prevent XSS
- Never expose sensitive information in client-side code

## Important Conventions

- **PascalCase**: Component files (e.g., `AlertTable.vue`)
- **camelCase**: Pages and functions (e.g., `alerts.vue`, `useAlerts`)
- **Composables**: Named as `use[Name]` (e.g., `useAuth`, `useAlerts`)
- **No classes**: Use functional programming patterns only
- **Git commits**: Never include "Co-Authored-By: Claude" in commit messages