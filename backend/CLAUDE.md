# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Prebetter backend.

**Note**: For overall project architecture and frontend integration, see the [root CLAUDE.md](../CLAUDE.md).

## Prebetter Backend Overview

FastAPI-based REST API serving Prelude IDS data with JWT authentication and user management.

## Quick Reference

```bash
# Start development server
fastapi dev

# Run tests with coverage
uv run pytest --cov

# Format and lint code  
ruff format . && ruff check . --fix

# Access API documentation
open http://localhost:8000/api/v1/docs
```

## Architecture Overview

### Dual Database System
- **Prelude DB**: Read-only IDS data (alerts, analyzers, heartbeats) - contains the security event data
- **Prebetter DB**: User management and authentication data - managed by the API
- Both use MySQL with SQLAlchemy ORM and connection pooling (pool_size=5, max_overflow=10)

### Layered Architecture
```
app/
├── api/          # Route definitions and request handling
├── core/         # Core utilities, config, security, logging
├── database/     # Database utilities, query builders, model converters
├── middleware/   # CORS, exception handling, request tracking
├── models/       # SQLAlchemy ORM models
├── schemas/      # Pydantic schemas for API validation
└── services/     # Business logic layer
```

### Security & Authentication

**Current Implementation:**
- JWT tokens with HS256 algorithm (8-hour expiration)
- Bcrypt password hashing (configurable rounds, default 14)
- Role-based access: superuser and regular user
- Request tracking via `X-Request-ID` header

**Known Limitations:**
- No token revocation/blacklist mechanism
- No logout endpoint (tokens valid until expiration)
- No refresh token support

## Common Commands

### Development
```bash
# Start dev server
uvicorn app.main:app --reload

# Or using FastAPI CLI
fastapi dev

# Run with specific host/port
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_alerts.py -v

# Run with coverage
pytest --cov=app

# Run with coverage report
uv run pytest --cov

# Run tests with maximum 1 failure
pytest --maxfail=1
```

### Linting & Formatting
```bash
# Check code with ruff
ruff check .

# Fix auto-fixable issues
ruff check . --fix

# Format code with ruff
ruff format .
```

### Database
```bash
# Load Prelude database dump
gunzip < prelude.sql.gz | mysql -u root -p prelude

# Connect to databases
mysql -u <username> -p prelude
mysql -u <username> -p prebetter
```

### Package Management (using uv)
```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac

# Install dependencies
uv sync

# Add new dependency
uv add <package-name>
```

## Environment Configuration

**Required** in `.env` file:
```env
# MySQL Connection (REQUIRED)
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_PRELUDE_DB=prelude
MYSQL_PREBETTER_DB=prebetter

# Security (CRITICAL - Change in production!)
SECRET_KEY=your-secure-random-key-here  # Used for JWT signing (32+ characters)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15         # Short-lived access tokens (auto-refreshed)
REFRESH_TOKEN_EXPIRE_DAYS=7            # Long-lived refresh tokens (session lifetime)
BCRYPT_ROUNDS=14

# Environment & Logging
ENVIRONMENT=development  # development|production
LOG_LEVEL=INFO          # DEBUG|INFO|WARNING|ERROR

# CORS (Restrict in production!)
BACKEND_CORS_ORIGINS=["http://localhost:3000"]  # Frontend URL
```

**Critical Notes**:
- The codebase uses `SECRET_KEY` for JWT signing (NOT `JWT_SECRET_KEY`)
- `REFRESH_TOKEN_EXPIRE_DAYS=7` MUST match frontend session maxAge (7 days)
- Ensure a strong, unique `SECRET_KEY` value (32+ characters) in production

## API Endpoints

### Authentication
- `POST /api/v1/auth/token` - Login (returns access + refresh token pair)
- `POST /api/v1/auth/refresh` - Exchange refresh token for new access token
- `GET /api/v1/auth/users/me` - Get current user info

### Core Endpoints (Protected)
- `/api/v1/alerts/` - Security alerts with filtering
- `/api/v1/statistics/timeline` - Alert timeline stats
- `/api/v1/statistics/summary` - Summary statistics
- `/api/v1/heartbeats/status` - Agent status monitoring
- `/api/v1/reference/classifications` - Alert classifications
- `/api/v1/users/` - User management (superuser only)

### Health & Monitoring
- `/health` - Application health check
- `/api/v1/docs` - Swagger UI documentation
- `/api/v1/redoc` - ReDoc documentation

## Authentication Flow

1. **Login**: `POST /api/v1/auth/token` with username/password
2. **Token Response**: `{"access_token": "...", "refresh_token": "...", "expires_in": 900, "token_type": "bearer"}`
3. **Protected Requests**: Include header `Authorization: Bearer <access_token>`
4. **Token Validation**: `get_current_user` validates token AND enforces `type: access`
5. **Token Refresh**: `POST /api/v1/auth/refresh` with refresh token to get new access token
6. **Expiration**: Access tokens expire after 15 minutes, refresh tokens after 7 days

## Code Patterns

### Query Construction Pattern

When creating new endpoints that query the database:

1. Use query builders from `database/query_builders.py` (e.g., `build_alert_base_query`)
2. Apply filters using `apply_standard_alert_filters`
3. Apply sorting using `apply_sorting` helper
4. Convert results using `database/models.py` converters (e.g., `alert_result_to_list_item`)

See `api/v1/routes/alerts.py` for reference implementations.

### Creating New Query Builders

Pattern for `database/query_builders.py`:
- Return tuple: `(query, model_dict)` where model_dict contains aliases
- Document all parameters and return values
- Use `outerjoin` for optional relationships

### Adding Model Converters

Pattern for `database/models.py`:
- Strong typing: `def result_to_schema(result: Row) -> Schema`
- Handle None/missing values
- Naming: `*_to_*` or `build_*`

## Common Utilities

### Join Conditions

The application uses common join conditions for various tables. These are centralized in `database/config.py`:

- `get_analyzer_join_conditions`: For Analyzer table joins
- `get_source_address_join_conditions`: For source Address table joins
- `get_target_address_join_conditions`: For target Address table joins
- `get_node_join_conditions`: For Node table joins

### Query Helpers

The application provides helper functions for common query operations:

- `apply_standard_alert_filters`: Apply standard filters to a query
- `apply_sorting`: Apply sorting to a query based on sort field and order

### Processing Large Result Sets

For operations that process a large number of records, always consider:

1. Using `limit()` to restrict the total number of records
2. Use `.distinct()` when appropriate to eliminate duplicates
3. For raw data export, use generators like in `generate_csv()` function
4. Consider adding early exit conditions in processing functions

## Troubleshooting

### Query Performance
- Use MySQL `EXPLAIN` to check indexes
- Always add `.limit()` to queries (max 100 for pagination)
- Use `.distinct()` to eliminate duplicates from joins
- Use `yield_per(1000)` for exports/large datasets

### SQLAlchemy Join Conditions
Use `and_()` for complex joins:
```python
.outerjoin(Entity, and_(
    Entity._message_ident == Parent._message_ident,
    Entity._parent_type == "A"
))
```

### Enum Handling
⚠️ Always use string keys in sort_options dictionaries, not Enum values:
```python
# Correct
sort_options = {"detect_time": DetectTime.time}

# Wrong - will fail
sort_options = {SortField.DETECT_TIME: DetectTime.time}
```

## API Documentation

- Interactive Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`


## Important Implementation Details

### Python & Dependencies
- **Python Version**: 3.13+ required
- **Package Manager**: `uv` (NOT pip or poetry)
- **Key Dependencies**: FastAPI, SQLAlchemy 2.0, Pydantic 2.0, PyJWT

### Database Specifics
- **Connection Pooling**: `pool_size=5, max_overflow=10`
- **Query Limits**: Always use `.limit()` to prevent large result sets
- **Distinct Results**: Use `.distinct()` to eliminate duplicates
- **Batch Processing**: Use `yield_per(1000)` for exports

### Security Considerations
- **Password Hashing**: Bcrypt with configurable rounds (default 14)
- **JWT Claims**: Currently only `sub`, `exp`, `iat`, `jti`
- **CORS**: Restricted by default via `BACKEND_CORS_ORIGINS`
- **⚠️ No Rate Limiting**: Login endpoint vulnerable to brute force
  - **Priority**: HIGH - Implement before production
  - **Solution**: Add slowapi library with `@limiter.limit("5/minute")`
- **⚠️ No Token Revocation**: Tokens valid until expiration, logout only clears frontend
  - **Mitigation**: 8-hour window + server-side storage reduces risk

### Operational Details
- **Timezone Handling**: All datetimes use UTC via `datetime_utils.ensure_timezone()`
- **Request Tracking**: Unique ID in `X-Request-ID` header
- **Health Endpoint**: `/health` returns database connectivity status
- **Logging**: Human-readable for dev, JSON for production

### Testing
- **Test Coverage**: Run `uv run pytest --cov`
- **Test Suite**: 112 tests across 12 test modules
- **Test Databases**: Uses separate test databases
- **Fixtures**: Database sessions provided via `conftest.py`
- **⚠️ CI/CD Gap**: Tests exist but don't run in GitHub Actions
  - **Priority**: URGENT - Add pytest step to CI pipeline

## Common Development Tasks

### Adding a New Protected Endpoint
Use `Depends(get_current_user)` dependency - see `api/v1/routes/*.py` for examples.

### Creating a Query with Filters
```python
query, models = build_alert_base_query(db)
query = apply_standard_alert_filters(query=query, severity="high", **models)
results = query.limit(100).all()
```

### Adding a New User
Use `UserService.create()` - see `api/v1/routes/users.py` for implementation.
