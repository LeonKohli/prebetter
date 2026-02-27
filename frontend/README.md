# Prebetter Frontend

Nuxt 4 application providing a modern IDS dashboard interface for Prelude IDS. Features real-time alert monitoring, heartbeat visualization, and user management.

## Tech Stack

- **Framework**: [Nuxt 4](https://nuxt.com/) with Vue 3 Composition API
- **UI Components**: [shadcn-vue](https://www.shadcn-vue.com/) + [Reka UI](https://reka-ui.com/)
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com/) with OKLCH color system
- **Tables**: [TanStack Table](https://tanstack.com/table)
- **Charts**: [ApexCharts](https://apexcharts.com/)
- **Forms**: [vee-validate](https://vee-validate.logaretm.com/) + [Zod 4](https://zod.dev/)
- **Auth**: [nuxt-auth-utils](https://github.com/atinux/nuxt-auth-utils) (server-side sessions)
- **Icons**: [@nuxt/icon](https://nuxt.com/modules/icon) with Lucide
- **Package Manager**: [Bun](https://bun.sh/)

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

The frontend uses a secure server-side proxy pattern:

1. User credentials are sent to the frontend server
2. Frontend authenticates with the backend and receives JWT tokens
3. Tokens are stored in encrypted server-side sessions (never exposed to the browser)
4. All API calls are proxied through the frontend server, which injects the JWT automatically
5. The browser only sees an httpOnly session cookie

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
