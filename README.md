# Prebetter

A dashboard for [Snort 3](https://www.snort.org/snort3) alerts stored in [OpenSearch](https://opensearch.org/), with alert filtering, IP-pair grouping, a timeline, alert details including the captured payload, live refresh, and user administration.

## Architecture

The Nuxt 4 frontend renders the UI and runs Better Auth against the Prebetter MySQL database. Better Auth owns users, password hashes, sessions, and signing keys.

Browser requests go through Nuxt's `/api/*` routes. The proxy obtains a short-lived JWT for the current session and forwards it to FastAPI. FastAPI verifies the signature through Better Auth's JWKS endpoint, checks the issuer and audience, and queries OpenSearch.

Alerts reach OpenSearch from outside this project: Snort writes `alert_json` lines, and an ingest pipeline stores them as ECS-style documents in daily indices. The backend only reads them. It needs index-level `read` on the index pattern and nothing else.

## Set up the project

Requirements:

- Python 3.13 or later and uv.
- Node.js matching `frontend/package.json` and Bun. CI uses Node 24.
- OpenSearch with the alert indices. CI tests OpenSearch 3.9.
- MySQL or MariaDB for the Better Auth database. CI tests MariaDB 11.4.

1. Install dependencies:

   ```sh
   cd backend
   uv sync --locked
   cd ../frontend
   bun install --frozen-lockfile
   ```

2. Copy each component's `.env.example` to `.env` and fill in its settings. Both components must use the same `BETTER_AUTH_URL`.
3. Follow the [backend setup](backend/README.md#set-up) to point the API at OpenSearch, or at a local node with sample data.
4. Follow the [frontend setup](frontend/README.md#set-up-authentication) to install the auth schema and create an administrator or migrate existing users.
5. Start the backend from `backend` with `uv run fastapi dev`. Start the frontend from `frontend` with `bun run dev`.

Open [the dashboard](http://localhost:3000) and [API documentation](http://localhost:8000/api/v1/docs).

## Upgrade an existing installation

Install from the committed lockfiles. Before starting Better Auth 1.7, apply [the JWKS migration](frontend/migrations/2026-09-07-jwks-algorithm.sql) once to an existing Better Auth database. Fresh installations use `frontend/better-auth-schema.sql`, which already includes those columns.

Deploy frontend and backend configuration together. The old `SECRET_KEY`, access/refresh-token settings, and `NUXT_SESSION_PASSWORD` do not configure the current auth system. The backend no longer reads any `MYSQL_*` setting; it needs the `OPENSEARCH_*` settings from `backend/.env.example`.

## Verify changes

From `backend`:

```sh
uv run ruff check .
uv run pytest
```

From `frontend`:

```sh
bun run test
bun run check
bun run test:e2e
bun run build
```

Backend tests need a disposable OpenSearch node, frontend end-to-end tests a disposable auth database. See the [backend test setup](backend/README.md#tests) and [frontend HTTP tests](frontend/README.md#checks). The [CI workflow](.github/workflows/checks.yml) provisions both and runs these checks.

## Development references

- [Backend setup, API, and query design](backend/README.md)
- [Frontend setup and authentication](frontend/README.md)

Licensed under [GPL-3.0](LICENSE).
