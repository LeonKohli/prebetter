# Prebetter frontend

Nuxt 4 and Vue 3 render the dashboard. UI components use shadcn-vue, Reka UI, and Tailwind CSS. Better Auth runs in the Nuxt server and stores users and sessions in MySQL.

## Set up authentication

From this directory:

```sh
bun install --frozen-lockfile
cp .env.example .env
```

Fill in the variables from `.env.example`:

| Variable | Purpose |
|---|---|
| `NUXT_API_BASE` | FastAPI base URL |
| `BETTER_AUTH_URL` | Public frontend origin, also the JWT issuer and audience |
| `BETTER_AUTH_SECRET` | Auth secret; generate with `openssl rand -hex 32` |
| `MYSQL_HOST`, `MYSQL_PORT` | Auth database server |
| `MYSQL_USER`, `MYSQL_PASSWORD` | Auth database credentials |
| `MYSQL_PREBETTER_DB` | Auth database name |

Use HTTPS for the production origin. Better Auth derives secure cookie behavior from its configuration and environment.

Create the database named by `MYSQL_PREBETTER_DB` through your database administration tooling. For a fresh auth database, import the schema. Export the connection variables for this shell command; `--password` prompts for the database password.

```sh
mariadb --host="$MYSQL_HOST" --port="$MYSQL_PORT" --user="$MYSQL_USER" --password "$MYSQL_PREBETTER_DB" < better-auth-schema.sql
```

For an existing Better Auth database upgrading to 1.7, apply the additive migration once instead:

```sh
mariadb --host="$MYSQL_HOST" --port="$MYSQL_PORT" --user="$MYSQL_USER" --password "$MYSQL_PREBETTER_DB" < migrations/2026-09-07-jwks-algorithm.sql
```

For an installation with legacy `users` rows, migrate them after creating the Better Auth tables:

```sh
bun run scripts/migrate-users.ts
```

This preserves bcrypt password hashes and leaves the legacy table intact. Do not run it on a fresh database without a `users` table.

For a fresh installation, export `ADMIN_USERNAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD`, then run:

```sh
bun run auth:create-admin
```

The command uses Better Auth's server API and does not enable public registration. Keep these values in the environment and remove them when finished. Administrators manage subsequent users from the profile page.

Start the frontend with `bun run dev`.

## Authentication contract

- Better Auth serves `/api/auth/*`, including username login, session lookup, logout, user administration, and JWKS.
- Public registration is disabled. The configured plugins are username, admin, and JWT.
- Sessions last seven days. JWTs last fifteen minutes. Both are configured in `server/utils/auth.ts`.
- The application proxies obtain JWTs server-side and inject them into FastAPI requests. Browser application code uses the session cookie.
- `useAuth()` stores session state in Nuxt `useState` for SSR and hydration. Route middleware refreshes it through `useRequestFetch()`.
- Protected pages declare `requiresAuth: true`; guest pages declare `guestOnly: true`.

## Tests

`bun run test` runs utility tests in Node without starting Nuxt or accessing MySQL. `bun run typecheck` checks the Nuxt application, and `bun run build` produces the server and client bundles.

`bun run test:e2e` starts the real Nuxt server on `127.0.0.1:43017`. It needs an explicitly exported `MYSQL_PREBETTER_DB` ending in `_test`, the other MySQL connection variables, and the current auth schema. Use a disposable database; tests create and remove users and sessions and may create signing keys.

The HTTP suite checks credentials, closed registration, session isolation, JWT verification, API error forwarding, both SSE proxies, and logout invalidation. Its local backend verifies real JWT signatures through the Nuxt JWKS endpoint. The test generates its own auth secret and origin.

## Dependency compatibility

- Keep TypeScript 6 until Vue's compiler tooling supports the [TypeScript 7 compiler API](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/).
- Keep Vitest within the peer range declared by `@nuxt/test-utils`.
- [TanStack Table v9](https://tanstack.com/table/latest/docs/framework/vue/guide/migrating) requires migration of table construction, state, and types. The current components use v8.

Check these upstream constraints before changing their major versions.

## UI conventions

Use Composition API, `<script setup lang="ts">`, and Nuxt auto-imports. Use the existing semantic Tailwind color tokens and shared UI components. Forms use vee-validate with Zod. Frontend-specific development guidance is in [CLAUDE.md](CLAUDE.md).
