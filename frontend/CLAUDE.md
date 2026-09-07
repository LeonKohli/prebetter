# Frontend development

Read [README.md](README.md) for setup, authentication, and verification commands.

## Vue and Nuxt

- Use `<script setup lang="ts">`, Composition API, and Nuxt auto-imports.
- Prefer computed state and `defineModel` over synchronization watchers. Use Vue first, Nuxt for application behavior, and VueUse for browser utilities.
- Use `shallowRef` when nested mutation tracking is unnecessary.
- Emit camelCase event names and use kebab-case listeners in templates.
- Keep shared request state in Nuxt `useState`. It persists across navigation and does not need unmount cleanup.
- Cancel timers, event listeners, and stream connections when their owner unmounts.
- Use the split Nuxt TypeScript configurations. Shared client/server contracts belong in `shared/types/`.

## Authentication and requests

- `server/utils/auth.ts` configures Better Auth. It owns database sessions, username login, admin operations, and JWT issuance.
- Use `authClient` for auth mutations and `useAuth()` for SSR-aware session state.
- Mark protected pages with `requiresAuth: true` and login pages with `guestOnly: true`.
- Fetch IDS data through `/api/*`. The Nuxt proxy obtains a session JWT and injects it into backend requests.
- Keep auth secrets and database credentials in server-only configuration.
- Preserve session isolation, logout invalidation, SSR cookie forwarding, and stream cancellation when changing auth or proxies.
- For a sliding date range, include the refresh signal in both the fetch key and the range calculation. A cached key alone cannot advance time.

## UI

- Use the existing shadcn-vue and Reka UI components.
- Use inline Tailwind classes and semantic color tokens such as `bg-background`, `text-foreground`, and `border-border`.
- Keep dark mode driven by the existing theme tokens. Avoid `@apply` and arbitrary palette colors.
- Use Lucide icons through the existing icon integrations.
- Use vee-validate and Zod for form validation.

## Checks

Run `bun run test`, `bun run typecheck`, and `bun run build`. Auth and proxy changes also require `bun run test:e2e` against a disposable auth database. Unit tests use Node; HTTP integration tests start the real Nuxt application and Better Auth.

TypeScript, Vitest, and TanStack Table upgrades must match their consumers. Check Vue compiler support, Nuxt test-utils peer dependencies, and the Table migration guide before changing their major versions.
