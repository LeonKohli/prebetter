# Prelude IDS API

FastAPI REST API that reads from a Prelude IDS database and exposes alerts, heartbeats, statistics, and user management over HTTP.

## Features

### User Management & Authentication

- JWT authentication with superuser and regular user roles
- CRUD for users (superuser only), password change/reset
- Race condition protection on concurrent user operations

### Alerts

- Paginated alert listing with filtering (severity, classification, IP, date range)
- Alert detail with source, target, and analyzer info
- Grouping by source/target IP pairs
- Full payload data in two forms: `readable` (UTF-8) and `original` (base64)

### Export

- CSV export with the same filtering options as the alert list endpoint

### Heartbeats

- Tree view of hosts and their agents (OS info, last heartbeat, online/offline)
- Heartbeat timeline over a configurable period
- Flat or grouped analyzer status list

### Statistics

- Timelines by hour, day, week, or month
- Summary stats: totals, severity distribution, top classifications, top IPs
- Grouped alert counts by various metrics

### Health check

`/health` endpoint reports "healthy", "degraded", or "unhealthy" based on database connectivity. Returns uptime and timestamp. Works with load balancers, k8s probes, etc.

### Logging

Every request gets a unique `X-Request-ID` (returned in response headers). Request duration and status are logged automatically.

Logging format depends on your environment:

#### Formatting
- **Development Mode**: Uses human-readable format for easier debugging:
  ```
  2023-10-09 14:30:45,123 - app.middleware.request_tracking - INFO - Request completed: GET /api/v1/alerts - Status: 200 - Duration: 0.470s
  ```

- **Production Mode**: Uses JSON-structured logging for machine parsing:
  ```json
  {
    "timestamp": "2023-10-09T14:30:45.123456",
    "level": "INFO",
    "message": "Request completed: GET /api/v1/alerts",
    "module": "request_tracking",
    "function": "request_middleware",
    "line": 42,
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
  ```

#### Log levels
Set `LOG_LEVEL` to control verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL). SQLAlchemy and Uvicorn are pinned to WARNING to keep things quiet.

## Project structure

```bash
app/
├── api/                    
│   ├── base.py            # Main router configuration that includes all v1 routes
│   └── v1/
│       └── routes/        
│           ├── alerts.py      # Alert management endpoints
│           ├── auth.py        # Authentication endpoints
│           ├── users.py       # User management endpoints
│           ├── reference.py   # Reference data endpoints
│           ├── statistics.py  # Statistics endpoints
│           ├── export.py      # Export alerts endpoint (CSV)
│           └── heartbeats.py  # Heartbeat monitoring endpoints
├── core/                  
│   ├── config.py          # Environment & app configuration
│   ├── security.py        # Authentication & security utilities
│   ├── logging.py         # Logging configuration
│   └── datetime_utils.py  # Datetime handling utilities
├── database/             
│   ├── config.py          # Database connection management
│   ├── init_db.py         # Database initialization and superuser setup
│   ├── models.py          # Model conversion utilities to convert database results to API schema models
│   └── query_builders.py  # Query building utilities
├── middleware/           
│   ├── cors.py            # CORS configuration
│   ├── exception_handlers.py # Global exception handlers
│   ├── request_tracking.py # Request ID and logging middleware
│   └── setup.py           # Centralized middleware configuration
├── models/               
│   ├── prelude.py         # SQLAlchemy models for IDS (reflected via automap)
│   └── users.py           # User models
├── schemas/              
│   ├── prelude.py         # IDS Pydantic models
│   └── users.py           # User Pydantic models
├── services/             
│   ├── users.py           # Business logic for user operations
│   └── health.py          # Health monitoring service
└── main.py                # Application entry point and lifespan configuration
```

## Database setup

Two MySQL databases:

1. **Prelude DB** — the IDS data (alerts, heartbeats, analyzers). Read-only, the API never writes to it.
2. **Prebetter DB** — user accounts and auth. Managed by the API.

Both connect through SQLAlchemy with connection pooling (5+10 overflow) and `pool_pre_ping`. Each DB has its own session factory.

### Required Accelerator: Prebetter_Pair (Pair-Key)

Grouped endpoints (list/count/details grouped by source/target IP) require the
`Prebetter_Pair` accelerator installed in the Prelude DB. The API verifies its
presence during startup and will fail fast if it's missing. There is no
Address-based fallback — this guarantees consistent performance and behavior.

- What it is: a helper table (`Prebetter_Pair`) maintained by triggers on
  `Prelude_Address` that stores one canonical IPv4 pair per message and a single
  `pair_key` (BIGINT). This enables grouping/counting by a single indexed key
  and removes heavy multi-table joins and multi-column DISTINCT.

- Install / Status / Backfill:
  ```bash
  # Install table + triggers
  uv run python -m app.scripts.prelude_pair_accelerator install

  # Backfill recent data (idempotent)
  uv run python -m app.scripts.prelude_pair_accelerator backfill-days --days 7

  # Check presence (table, triggers, indexes) and row count
  uv run python -m app.scripts.prelude_pair_accelerator status

  # Uninstall (remove triggers; optional table drop)
  uv run python -m app.scripts.prelude_pair_accelerator uninstall [--drop-table]
  ```

- Preboot checklist (must pass):
  1) `uv run python -m app.scripts.prelude_pair_accelerator status`
  2) `uv run python -m app.scripts.prelude_index_maintenance check` (ensure `idx_dt_time_ident_gmtoff` exists)
  3) Start the API; it will verify the accelerator and refuse to start if missing

See `docs/prelude-slow-query-analysis.md` for the detailed design, schema,
triggers, and troubleshooting guidance.

## Application lifecycle

On startup: verifies DB connections, validates schema, creates tables, initializes health state. On shutdown: closes connections cleanly.

## Setup

1. **Clone the repository**

2. **Create a Virtual Environment:**

   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies:**

   ```bash
   uv sync
   ```

4. **Configure Environment Variables:**
   - Copy the example file and update your credentials:

     ```bash
     cp .env.example .env
     ```

   - Required variables:
     - Database credentials (MySQL settings for both Prelude and Prebetter).
     - `SECRET_KEY`: For JWT token generation.
     - `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time.

5. **Start the API Server:**

   ```bash
   fastapi dev
   ```

6. **Create Initial User Account:**

   The system no longer automatically creates default credentials for security reasons.
   You must manually create your first user account:

   ```bash
   uv run python -m app.scripts.create_user
   ```

   The script will:
   - Prompt for username, email, and password
   - Ask if you want to create a superuser (admin)
   - Show a summary and ask for confirmation
   - Create the user in the database
   
## API endpoints

Full interactive docs available at [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs) (Swagger UI) when the server is running. Here's the overview:

| Group | Endpoints | What they do |
|-------|-----------|-------------|
| Auth | `POST /api/v1/auth/token`, `/refresh`, `/users/me` | Login, token refresh, current user |
| Users | `GET/POST/PUT/DELETE /api/v1/users/` | User CRUD (superuser only), password management |
| Alerts | `GET /api/v1/alerts/`, `/alerts/groups`, `/alerts/{id}` | List, group by IP pair, detail with full payload |
| Export | `GET /api/v1/export/alerts/{format}` | CSV export with same filters as alert list |
| Heartbeats | `GET /api/v1/heartbeats/tree`, `/timeline`, `/status` | Agent tree, timeline, online/offline status |
| Statistics | `GET /api/v1/statistics/timeline`, `/summary` | Time-bucketed counts, summary with top IPs |
| Reference | `GET /api/v1/reference/classifications`, `/severities`, `/servers` | Filter dropdown values |
| Health | `GET /health` | DB connectivity, uptime, overall status |

All list endpoints support pagination (`page`, `size`) and most accept filters for severity, classification, IP, date range, and server.

## Environment variables

See `.env.example` for all variables with defaults. The important ones:

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `SECRET_KEY` | Yes | — | JWT signing key, 32+ chars |
| `MYSQL_USER` | Yes | — | |
| `MYSQL_PASSWORD` | Yes | — | |
| `MYSQL_HOST` | No | localhost | |
| `MYSQL_PORT` | No | 3306 | |
| `MYSQL_PRELUDE_DB` | No | prelude | |
| `MYSQL_PREBETTER_DB` | No | prebetter | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | 15 | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | 7 | |
| `BCRYPT_ROUNDS` | No | 14 | Lower = faster, less secure |
| `BACKEND_CORS_ORIGINS` | No | `["http://localhost:3000"]` | JSON array |
| `ENVIRONMENT` | No | development | `development` or `production` (changes log format) |
| `LOG_LEVEL` | No | INFO | Standard Python log levels |

## Development

### Requirements

- Python 3.13+
- uv package manager (for dependency management)
- MySQL 5.7+ (for both Prelude and Prebetter databases)

### Tools

- Ruff for linting and formatting
- pytest with coverage

### Commands

```bash
# Run tests with coverage
uv run pytest --cov

# Run linter
ruff check . # or using with --fix for 

# Format code
ruff format .
```

## Testing

Run the test suite using [pytest](https://docs.pytest.org/):

```bash
# Optionally set PYTHONPATH to include the project root
export PYTHONPATH=$PYTHONPATH:$(pwd)
uv run pytest --cov
```

Covers endpoints, validation, filtering, pagination, statistics, and edge cases.

## Performance notes

- Connection pooling via SQLAlchemy (pool_size=5, max_overflow=10)
- Progressive filtering (most selective first) for better query plans
- Separate count queries to avoid slow `COUNT(*)` on joined results
- All dates are timezone-aware (UTC internally)

## Security

- JWT auth with bcrypt password hashing (configurable rounds)
- Superuser/regular user roles
- Can't delete the last superuser
- Error responses don't leak internals
- Request IDs on every response for audit trails

## Middleware

Three layers: CORS (configurable origins), request tracking (`X-Request-ID` + duration logging), and a global exception handler that returns consistent error shapes.

## Data models

All schemas are Pydantic models in `app/schemas/`. The main ones:

- **Alert list item** — id, message_id, timestamps, severity, classification, source/target IPs, analyzer
- **Alert detail** — everything above plus network info, protocol, process, payload data (`readable` UTF-8 + `original` base64)
- **Grouped alert** — alerts grouped by source/target IP pair with counts and classification breakdown
- **User** — email, username, full_name, is_superuser, timestamps
- **Health** — status ("healthy"/"degraded"/"unhealthy"), DB connectivity, uptime
