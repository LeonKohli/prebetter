# Prebetter backend

FastAPI serves Prelude alerts, statistics, heartbeats, reference filters, and CSV exports. It verifies Better Auth JWTs through JWKS. User and session management belong to the [Nuxt frontend](../frontend/README.md).

## Set up Prelude

From this directory:

```sh
uv sync --locked
cp .env.example .env
```

Fill in all required settings from `.env.example`. `BETTER_AUTH_URL` must match the frontend origin because it defines the expected JWT issuer, audience, and JWKS location. Use the existing Prelude database for IDS data and the Prebetter database provisioned by the frontend setup.

The API requires the `Prebetter_Pair` accelerator. Install it and backfill the required data window:

```sh
uv run python -m app.scripts.prelude_pair_accelerator install
uv run python -m app.scripts.prelude_pair_accelerator backfill-days --days 7
uv run python -m app.scripts.prelude_pair_accelerator status
uv run python -m app.scripts.prelude_index_maintenance check
```

These commands modify the Prelude schema or data. Read the [maintenance guide](app/scripts/README.md) before applying them to an existing installation. The API refuses startup when the accelerator table, required triggers, or indexes are missing.

Start the API:

```sh
uv run fastapi dev
```

The frontend must be reachable at `BETTER_AUTH_URL` when the API needs to fetch signing keys. Backend startup does not install Better Auth tables or create users.

## API reference

| Group | Paths under `/api/v1` |
|---|---|
| Alerts | `/alerts/`, `/alerts/groups`, alert detail/deletion routes, `/alerts/stream` |
| Statistics | `/statistics/timeline`, `/statistics/summary` |
| Heartbeats | `/heartbeats/status`, `/heartbeats/timeline`, `/heartbeats/stream` |
| Export | `/export/alerts/{format}` |
| Reference | `/reference/classifications`, `/reference/severities`, `/reference/servers` |

The registered routers in `app/api/base.py` and the [OpenAPI documentation](http://localhost:8000/api/v1/docs) define the exact request and response contracts. Protected routes use Bearer authentication. Administrator operations require the `admin` role.

`/health` reports startup state and database availability. `/` links to the API documentation.

## Database behavior

Prelude queries use SQLAlchemy and the existing Prelude schema. Alert listing and grouping use `Prebetter_Pair` to avoid address-join fan-out. Exports stream batches rather than loading the full result into memory.

The connection is not read-only. Alert deletion removes IDS records, and maintenance scripts manage indexes, triggers, and accelerator rows. Use database permissions appropriate to the operations enabled in your deployment.

Keep timestamps timezone-aware and in UTC. Response conversion lives in `app/database/models.py`; Pydantic response schemas live in `app/schemas/`.

## Tests

Run linting and tests from this directory:

```sh
uv run ruff check .
uv run pytest
```

Use disposable databases for the full suite. Initialize an empty Prelude test database with `prelude_structure.sql`. This file contains `DROP TABLE` statements and must never be imported into a database containing data you need.

Export the MySQL settings, `BETTER_AUTH_URL`, `ENVIRONMENT`, `LOG_LEVEL`, and `BACKEND_CORS_ORIGINS` for the test environment. Alternatively, put test-specific settings in `.env.test`. Exported variables take precedence.

The fixtures create the `Prebetter_Pair` table with DDL, then seed IDS data inside a transaction. Each test uses a savepoint, and the outer transaction rolls back at suite completion. The initial DDL is not rolled back.

For checks without a database connection:

```sh
uv run pytest tests/test_auth_jwks.py tests/test_datetime_utils.py tests/test_filters.py tests/test_db_models_conversion.py tests/test_health.py
```

The [CI workflow](../.github/workflows/checks.yml) provisions disposable MariaDB databases and runs the complete suite.
