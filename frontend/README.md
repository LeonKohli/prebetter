# Prebetter Frontend

Nuxt 4 frontend for the Prebetter IDS dashboard. Handles alert views, heartbeat monitoring, charts, and user management.

## Tech stack

Built on [Nuxt 4](https://nuxt.com/) with Vue 3 Composition API. UI uses [shadcn-vue](https://www.shadcn-vue.com/) and [Reka UI](https://reka-ui.com/) on top of [Tailwind CSS v4](https://tailwindcss.com/) (OKLCH color system for theming). Tables powered by [TanStack Table](https://tanstack.com/table), charts by [ApexCharts](https://apexcharts.com/). Forms use [vee-validate](https://vee-validate.logaretm.com/) with [Zod 4](https://zod.dev/) for validation. Auth handled by [nuxt-auth-utils](https://github.com/atinux/nuxt-auth-utils) with server-side sessions. Uses [Bun](https://bun.sh/) as package manager.

## Quick Start

```bash
# Install dependencies
bun install

# Copy environment config
cp .env.example .env
# Edit .env with your session password

# Start development server
bun run dev
```

The frontend expects the backend API to be running at `http://localhost:8000` (configurable via `NUXT_API_BASE`).

## Scripts

| Command | Description |
|---------|-------------|
| `bun run dev` | Start development server (port 3000) |
| `bun run build` | Build for production |
| `bun run preview` | Preview production build |
| `bun run typecheck` | Run TypeScript type checking |
| `bun run test` | Run tests with Vitest |

## Project Structure

```
frontend/
├── app/                        # Nuxt 4 app directory
│   ├── assets/css/            # Tailwind CSS entry point
│   ├── components/            # Vue components
│   │   ├── ui/               # shadcn-vue base components
│   │   ├── alerts/           # Alert-specific components
│   │   ├── profile/          # Profile page components
│   │   ├── Navbar.vue        # App navigation
│   │   └── ...               # Shared components
│   ├── composables/          # Auto-imported composables
│   ├── layouts/              # Layout templates
│   ├── middleware/            # Route middleware
│   │   └── auth.global.ts    # Global auth guard
│   ├── pages/                # File-based routing
│   │   ├── index.vue         # Dashboard (protected)
│   │   ├── login.vue         # Login (guest only)
│   │   ├── profile.vue       # User profile (protected)
│   │   └── heartbeats/       # Heartbeat views
│   └── utils/                # Utility functions
├── server/                    # Nitro server
│   └── api/                  # Server API routes
│       ├── [...].ts          # Catch-all API proxy
│       └── auth/             # Auth endpoints
├── shared/                    # Shared client/server code
│   └── types/                # TypeScript declarations
├── nuxt.config.ts            # Nuxt configuration
└── vitest.config.ts          # Test configuration
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NUXT_SESSION_PASSWORD` | Session encryption key (min 32 chars) | Yes |
| `NUXT_API_BASE` | Backend API URL (default: `http://localhost:8000`) | No |

See `.env.example` for a complete template.

## Authentication

Tokens never touch the browser. Here's how it works:

1. User logs in, credentials go to the Nuxt server
2. Server authenticates with the backend, gets JWT tokens
3. Tokens are stored in an encrypted server-side session
4. All API calls go through the Nuxt server, which injects the token
5. Browser only ever sees an httpOnly session cookie

## Development

### Adding UI Components

```bash
bunx shadcn-vue@latest add <component-name>
```

### Styling Guidelines

- Use Tailwind CSS utility classes (no `@apply`)
- Use design tokens (`bg-background`, `text-foreground`, etc.) instead of arbitrary colors
- Dark mode is handled automatically via the OKLCH color system

### Key Conventions

- Vue 3 Composition API with `<script setup lang="ts">`
- Auto-imports for Vue/Nuxt functions (no manual imports needed)
- All API calls go through `/api/*` proxy routes
- `definePageMeta({ requiresAuth: true })` for protected pages

## License

GPL-3.0 - See [LICENSE](../LICENSE) for details.
