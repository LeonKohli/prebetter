# Prebetter

A dashboard for [Prelude IDS](https://www.prelude-siem.org/) with alert filtering, IP-pair grouping, timelines, heartbeat monitoring, CSV export, alert deletion, and user administration.

## Architecture

The Nuxt 4 frontend renders the UI and runs Better Auth against the Prebetter MySQL database. Better Auth owns users, password hashes, sessions, and signing keys.

Browser requests go through Nuxt's `/api/*` routes. The proxy obtains a short-lived JWT for the current session and forwards it to FastAPI. FastAPI verifies the signature through Better Auth's JWKS endpoint, checks the issuer and audience, and queries the Prelude database.

Prelude contains IDS data and the required `Prebetter_Pair` accelerator. Deletion and maintenance operations write to this database. It is not a read-only connection.

## Set up the project

Requirements:

- Python 3.13 or later and uv.
- Node.js matching `frontend/package.json` and Bun. CI uses Node 24.
- MySQL or MariaDB with the Prelude schema. CI tests MariaDB 11.4.
- Separate Prelude and Prebetter databases and credentials with the required permissions.

1. Install dependencies:

   ```sh
   cd backend
   uv sync --locked
   cd ../frontend
   bun install --frozen-lockfile
   ```

2. Copy each component's `.env.example` to `.env` and fill in its settings. Both components must use the same `BETTER_AUTH_URL`.
3. Follow the [backend setup](backend/README.md#set-up-prelude) to install the Prelude accelerator and indexes.
4. Follow the [frontend setup](frontend/README.md#set-up-authentication) to install the auth schema and create an administrator or migrate existing users.
5. Start the backend from `backend` with `uv run fastapi dev`. Start the frontend from `frontend` with `bun run dev`.

Open [the dashboard](http://localhost:3000) and [API documentation](http://localhost:8000/api/v1/docs).

## Upgrade an existing installation

Install from the committed lockfiles. Before starting Better Auth 1.7, apply [the JWKS migration](frontend/migrations/2026-09-07-jwks-algorithm.sql) once to an existing Better Auth database. Fresh installations use `frontend/better-auth-schema.sql`, which already includes those columns.

Deploy frontend and backend configuration together. The old `SECRET_KEY`, access/refresh-token settings, and `NUXT_SESSION_PASSWORD` do not configure the current auth system.

## Verify changes

From `backend`:

```sh
uv run ruff check .
uv run pytest
```

From `frontend`:

```sh
bun run test
bun run typecheck
bun run test:e2e
bun run build
```

Database tests require disposable schemas. See the [backend test setup](backend/README.md#tests) and [frontend HTTP tests](frontend/README.md#tests). The [CI workflow](.github/workflows/checks.yml) provisions MariaDB and runs these checks.

## Development references

- [Backend setup and API](backend/README.md)
- [Frontend setup and authentication](frontend/README.md)
- [Prelude maintenance commands](backend/app/scripts/README.md)
- [Query performance analysis](docs/prelude-slow-query-analysis.md)

Licensed under [GPL-3.0](LICENSE).
