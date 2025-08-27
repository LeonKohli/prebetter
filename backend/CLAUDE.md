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
- JWT tokens with HS256 algorithm (30-minute expiration)
- Bcrypt password hashing (default 12 rounds)
- Role-based access: superuser and regular user
- Request tracking via `X-Request-ID` header

**Known Limitations:**
- No token revocation/blacklist mechanism
- No refresh token support
- No logout endpoint (tokens valid until expiration)
- Conflicting secret key configuration (JWT_SECRET_KEY vs SECRET_KEY)

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
SECRET_KEY=your-secure-random-key-here  # Used for JWT signing
ACCESS_TOKEN_EXPIRE_MINUTES=30         # Token expiration time

# Environment & Logging
ENVIRONMENT=development  # development|production
LOG_LEVEL=INFO          # DEBUG|INFO|WARNING|ERROR

# CORS (Restrict in production!)
BACKEND_CORS_ORIGINS=["http://localhost:3000"]  # Frontend URL
```

**Note**: The codebase uses `SECRET_KEY` for JWT signing (not `JWT_SECRET_KEY`). Ensure a strong, unique value in production.

## API Endpoints

### Authentication
- `POST /api/v1/auth/token` - Login (returns JWT access token)
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
2. **Token Response**: `{"access_token": "...", "token_type": "bearer"}`
3. **Protected Requests**: Include header `Authorization: Bearer <token>`
4. **Token Validation**: Automatic via `get_current_user` dependency
5. **Expiration**: Tokens expire after 30 minutes (no refresh mechanism)

## Code Patterns

### Query Construction Pattern

When creating new endpoints that query the database, follow this pattern:

1. Use query builders from `database/query_builders.py` to construct base queries
2. Apply standard filters using `apply_standard_alert_filters` function
3. Apply sorting using the `apply_sorting` helper function
4. Use model conversion utilities from `database/models.py` to transform results

Example:

```python
# Get base query from query builder
query, models = build_alert_base_query(db)

# Apply standard filters
query = apply_standard_alert_filters(
    query=query,
    severity=severity,
    classification=classification,
    start_date=start_date,
    end_date=end_date,
    source_ip=source_ip,
    target_ip=target_ip,
    analyzer_model=analyzer_model,
    **models,
    Impact=Impact,
    Classification=Classification,
    DetectTime=DetectTime,
    Analyzer=Analyzer
)

# Apply sorting - always use string keys in sort_options
sort_options = {
    "detect_time": DetectTime.time,
    "severity": Impact.severity,
    "classification": Classification.text,
    # ... other options
}
query = apply_sorting(query, sort_by, sort_order, sort_options, default_column=Alert._ident)

# Process results
items = [alert_result_to_list_item(result) for result in results]
```

### Creating New Query Builders

When adding new query functionality:

1. Define a function in `database/query_builders.py`
2. Return both the query and any model aliases used
3. Document parameters and return values

Example:

```python
def build_new_query(db: Session, param1: str):
    """
    Build a query for some new functionality.
    
    Args:
        db: SQLAlchemy database session
        param1: Some parameter
        
    Returns:
        SQLAlchemy query object and a dict of model aliases
    """
    # Create model aliases
    some_alias = aliased(SomeModel)
    
    # Build query
    query = (
        db.query(
            # ... query fields
        )
        .join(...)
        .outerjoin(...)
    )
    
    return query, {"some_alias": some_alias}
```

### Adding Model Converters

When adding new model conversion functions to `database/models.py`:

1. Create strongly-typed functions with comprehensive docstrings
2. Handle edge cases (None values, missing attributes)
3. Follow naming pattern: `*_to_*` or `build_*`

Example:

```python
def some_result_to_schema(result: Row) -> SomeSchema:
    """
    Convert a query result to a schema object.
    
    Args:
        result: Query result row
        
    Returns:
        Populated schema object
    """
    return SomeSchema(
        id=result.id,
        name=result.name,
        # ... other fields
    )
```

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

## Troubleshooting Common Issues

### Query Performance

If queries are slow:

1. Check if the correct indexes are being used in MySQL (use `EXPLAIN`)
2. Consider if the query can be optimized (fewer joins, more specific conditions)
3. Look at fetching only the specific columns needed
4. Add appropriate limits to queries:
   ```python
   # Limit results to a reasonable number
   query = query.limit(1000)
   ```
5. Use `.distinct()` to eliminate duplicate rows
6. For grouped data, ensure that group_by clauses come before limit/offset clauses
7. For exports and large datasets, use `yield_per()` to process in batches:
   ```python
   # Process in batches instead of loading all at once
   results = query.yield_per(1000)
   ```

### SQLAlchemy Join Conditions

For complex join conditions, remember the pattern:

```python
.outerjoin(
    Entity,
    and_(
        Entity._message_ident == Parent._message_ident,
        Entity._parent_type == "A",
        # Additional conditions...
    ),
)
```

### Enum Handling

When working with Enum values:

1. Always use string keys in dictionaries, not Enum values:
```python
# Correct
sort_options = {
    "detect_time": DetectTime.time,
    "severity": Impact.severity,
}

# Incorrect - will lead to errors
sort_options = {
    SortField.DETECT_TIME: DetectTime.time,
    SortField.SEVERITY: Impact.severity,
}
```

2. Convert Enum values to strings when using as keys:
```python
# Extract string value from enum
sort_key = sort_by
if hasattr(sort_by, "value"):
    sort_key = sort_by.value
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
- **Password Hashing**: Bcrypt with 12 rounds (consider increasing to 14+)
- **JWT Claims**: Currently only `sub`, `exp`, `iat`, `jti`
- **CORS**: Currently allows all origins - MUST restrict in production
- **No Rate Limiting**: Consider implementing for login endpoints

### Operational Details
- **Timezone Handling**: All datetimes use UTC via `datetime_utils.ensure_timezone()`
- **Request Tracking**: Unique ID in `X-Request-ID` header
- **Health Endpoint**: `/health` returns database connectivity status
- **Logging**: Human-readable for dev, JSON for production

### Testing
- **Test Coverage**: Run `uv run pytest --cov`
- **Test Databases**: Uses separate test databases
- **Fixtures**: Database sessions provided via `conftest.py`

## Common Development Tasks

### Adding a New Protected Endpoint
```python
from fastapi import APIRouter, Depends
from app.api.v1.routes.auth import get_current_user

router = APIRouter()

@router.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    return {"user": current_user.username}
```

### Creating a Query with Filters
```python
from app.database.query_builders import build_alert_base_query
from app.database.utils import apply_standard_alert_filters

query, models = build_alert_base_query(db)
query = apply_standard_alert_filters(query=query, severity="high", **models)
results = query.limit(100).all()
```

### Adding a New User
```python
from app.services.users import UserService

user_service = UserService(db)
new_user = user_service.create(
    username="newuser",
    email="user@example.com", 
    password="securepassword",
    is_superuser=False
)
```