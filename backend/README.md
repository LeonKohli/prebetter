# Prelude IDS API

A FastAPI-based REST API for accessing Prelude IDS data with user management and authentication. This API provides comprehensive access to security alerts and related information from your Prelude IDS.

## Features

### User Management & Authentication

- **User Authentication:** JWT-based authentication system.
- **Role-Based Access:** Superuser and regular user roles.
- **User Operations:**
  - Create/Update/Delete users (superuser only).
  - Password management (change/reset).
  - Email and username validation.
  - Pagination for user listing.
- **Concurrent Operation Handling:** Protection against race conditions in user operations.

### Alert Management

- **Paginated Alerts Listing:** Browse alerts with rich filtering options.
- **Detailed Alert Information:** Retrieve comprehensive details including source, target, and analyzer information.
- **Alert Grouping:** Group alerts by source and target IP addresses.
- **Payload Access:** View full payload data in two representations: readable `readable` and original `original` (base64), without truncation.
- **Multi-Format Support:** Handles multiple alert formats and protocols.

### Export Functionality

- **Export Alerts:** Export alerts in CSV format.
  - Supports filtering by alert IDs, date ranges, severity, classification, source IP, target IP, and analyzer model.
  - Returns a downloadable CSV file with headers and alert data.

### Heartbeat Monitoring

- **Heartbeats Tree View:** Retrieve a tree view of hosts and their associated agents including operating system information, last heartbeat timestamps, and current status.
- **Heartbeats Timeline:** Generate a timeline of heartbeat events over a specified period, useful for monitoring agent activity.
- **Heartbeats Status:** Get a flat list or grouped view of all analyzers with their current status (online/offline) and detailed information.

### Data Analysis

- **Timeline Visualization:** Generate timelines based on hourly, daily, weekly, or monthly intervals.
- **Statistical Summaries:** View total alert counts and distributions by severity, classification, and analyzer.
- **Top Metrics:** Identify top classifications and source/target IP addresses.
- **Grouped Data:** Get alerts grouped by various metrics for an aggregated view.

### Health Monitoring System

- **Health Status Endpoint:** Dedicated `/health` endpoint for infrastructure monitoring.
- **Status Reporting:** Reports system status as "healthy", "degraded", or "unhealthy" based on component availability.
- **Database Connectivity:** Monitors both Prelude and Prebetter database connections.
- **Uptime Metrics:** Provides API uptime statistics and server timestamp.
- **Integration Ready:** Designed for load balancers, monitoring systems, Kubernetes probes, and Docker health checks.

### Request Tracking and Logging

- **Request ID Generation:** Assigns unique IDs to each request for traceability.
- **Response Headers:** Adds `X-Request-ID` to response headers for client-side tracking.
- **Performance Metrics:** Logs request duration and completion status.
- **Structured Logging:** Enhances logs with request context for easier troubleshooting.
- **Error Traceability:** Includes request IDs in error responses for correlation.

### Logging System

The API implements a flexible logging system that adapts based on your environment:

#### Environment-Based Formatting
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

#### Log Level Control
The `LOG_LEVEL` environment variable controls which messages are displayed:
- Higher levels (like WARNING) show fewer, more important messages
- Lower levels (like DEBUG) show more detailed information
- Noisy libraries (SQLAlchemy, Uvicorn) are automatically set to WARNING level

#### Request Tracking
All HTTP requests are logged with:
- Unique request ID (also returned in response headers as `X-Request-ID`)
- HTTP method and path
- Response status code
- Request duration in seconds

## Project Structure

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

## Database Structure

The application uses two separate MySQL databases:

1. **Prelude Database**: Contains all IDS data including alerts, heartbeats, and analyzer information. This database is treated as read-only by the API.

2. **Prebetter Database**: Contains user management data. This database is managed by the API for user authentication and authorization.

The connection to these databases is handled through SQLAlchemy with:
- Connection pooling (pool size: 5, max overflow: 10)
- Connection validation via `pool_pre_ping`
- Separate session factories for each database
- Query optimization with index-friendly filters
- Standardized join conditions for entity relationships
- Timezone-aware date handling

## Application Lifecycle

The API implements a structured lifecycle management approach:

1. **Startup Phase:**
   - Database connection verification
   - Schema validation
   - Database tables creation
   - Health state initialization

2. **Runtime Phase:**
   - Request processing with middleware pipeline
   - Database session management
   - Error handling and recovery

3. **Shutdown Phase:**
   - Graceful connection termination
   - Resource cleanup

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

5. **Import a dump of the Prelude Database (if needed for testing and development):**

   ```bash
   gunzip < prelude.sql.gz | mysql -u root -p prelude
   ```

6. **Start the API Server:**

   ```bash
   fastapi dev
   ```

7. **Create Initial User Account:**

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
   
## API Endpoints

### Authentication & User Management

- **Login:** `POST /api/v1/auth/token`
  - Request body: Form data with username and password.
  - Returns: JWT access token.

- **Current User:** `GET /api/v1/auth/users/me`
  - Returns: Current authenticated user's details.

- **Users (Superuser Only):**
  - **List Users:** `GET /api/v1/users/`
    - Supports pagination with `page` and `size` parameters.
    - `page`: Page number (default: 1)
    - `size`: Items per page (default: 10, max: 100)
  - **Create User:** `POST /api/v1/users/`
  - **Get User:** `GET /api/v1/users/{user_id}`
  - **Update User:** `PUT /api/v1/users/{user_id}`
  - **Delete User:** `DELETE /api/v1/users/{user_id}`

- **Password Management:**
  - **Change Password:** `POST /api/v1/users/change-password`
  - **Reset Password (Superuser):** `POST /api/v1/users/{user_id}/reset-password`

### Alert Management

- **List Alerts:** `GET /api/v1/alerts/`
  - **Query Parameters:**
    - `page`: Page number (default: 1)
    - `size`: Items per page (default: 10, max: 100)
    - `sort_by`: Sort field (`detected_at`, `created_at`, `severity`, `classification`, `source_ip`, `target_ip`, `analyzer`, `id`)
    - `sort_order`: Sort order (`asc`, `desc`)
    - `severity`: Filter by severity.
    - `classification`: Filter by classification text (partial match supported).
    - `start_date`: Start date in ISO format.
    - `end_date`: End date in ISO format.
    - `source_ip`: Filter by source IP (exact match).
    - `target_ip`: Filter by target IP (exact match).
    - `analyzer_model`: Filter by analyzer model.

- **Grouped Alerts:** `GET /api/v1/alerts/groups`
  - Supports the same query parameters as the alerts listing endpoint.
  - Groups alerts by source and target IP addresses and provides a classification breakdown per group.

- **Alert Detail:** `GET /api/v1/alerts/{alert_id}`
  - Returns: Detailed alert information including network, analyzer, and full payload data. Fields include `id`, `message_id`, `created_at`, `detected_at`, etc.
  - Byte-string entries in `additional_data` preserve fidelity with a simple structure:
    - `readable`: UTF-8 decoded (with replacement for undecodable bytes)
    - `original`: Base64-encoded original bytes (JSON-safe)

### Export Alerts

- **Export Alerts (CSV):** `GET /api/v1/export/alerts/{format}`
  - **Path Parameter:**
    - `format`: Currently only supports `csv`.
  - **Query Parameters:**
    - `alert_ids`: A list of specific alert IDs to export.
    - `start_date`: Start date for filtering (ISO format).
    - `end_date`: End date for filtering (ISO format).
    - `severity`: Filter by severity.
    - `classification`: Filter by classification text.
    - `source_ip`: Filter by source IP.
    - `target_ip`: Filter by target IP.
    - `analyzer_model`: Filter by analyzer model.
  - Returns: A streaming CSV file containing alert data with a header row (including fields like `id`, `created_at`, `detected_at`, etc.).

### Heartbeat Monitoring

- **Heartbeats Tree View:** `GET /api/v1/heartbeats/tree`
  - Returns: A JSON tree view of hosts and their associated agents, including:
    - Host OS information.
    - List of agents with details such as analyzer name, model, version, class, last heartbeat timestamp (`latest_heartbeat_at`), and online/offline status.

- **Heartbeats Timeline:** `GET /api/v1/heartbeats/timeline`
  - **Query Parameters:**
    - `hours`: Number of past hours to include in the timeline (default: 24, min: 1, max: 168).
    - `page`: Page number (default: 1).
    - `size`: Items per page (default: 100, min: 1, max: 1000).
  - Returns: Timeline data of heartbeat events with agent name, node details, timestamp (`timestamp`), and model.

- **Heartbeats Status:** `GET /api/v1/heartbeats/status`
  - **Query Parameters:**
    - `days`: Number of days to look back (default: 1, min: 1, max: 30).
    - `group_by_host`: Boolean flag to group results by host (default: false).
    - `start_date`: Optional start date for analysis.
    - `end_date`: Optional end date for analysis.
    - `severity`: Optional filter by severity.
  - Returns: List of analyzers with their current status (online/offline) or a tree structure grouped by host.

### Statistics and Analysis

- **Timeline Data:** `GET /api/v1/statistics/timeline`
  - **Query Parameters:**
    - `time_frame`: Grouping interval (`hour`, `day`, `week`, `month`).
    - `start_date`: Optional start date for analysis.
    - `end_date`: Optional end date for analysis.
    - `severity`: Optional filter by severity.
    - `classification`: Optional filter by classification.
    - `analyzer_name`: Optional filter by analyzer name.
  - Returns: Timeline data points with counts aggregated per time bucket.

- **Statistics Summary:** `GET /api/v1/statistics/summary`
  - **Query Parameter:**
    - `time_range`: Time range in hours to analyze (default: 24, min: 1, max: 720).
  - Returns: Overall statistics including total alerts, distribution by severity, classification, analyzer, top source/target IP addresses, and the analysis time range (`start_at`, `end_at`).

### Reference Data

- **Classifications:** `GET /api/v1/classifications`
- **Severities:** `GET /api/v1/severities`
- **Analyzers:** `GET /api/v1/analyzers`

### Health Monitoring

- **Health Check:** `GET /health`
  - Returns: Health status information including:
    - Overall status: "healthy", "degraded", or "unhealthy"
    - Database availability for both Prelude and Prebetter
    - API uptime in seconds
    - Current server timestamp

## Documentation

- **Interactive API Documentation:** [http://localhost:8000](http://localhost:8000)

## Environment Variables

- `MYSQL_USER`: MySQL username.
- `MYSQL_PASSWORD`: MySQL password.
- `MYSQL_HOST`: MySQL host (default: localhost).
- `MYSQL_PORT`: MySQL port (default: 3306).
- `MYSQL_PRELUDE_DB`: Name of the Prelude database (default: prelude).
- `MYSQL_PREBETTER_DB`: Name of the Prebetter database (default: prebetter).
- `SECRET_KEY`: Secret key for JWT token generation (required).
- `ALGORITHM`: Algorithm used for JWT (default: HS256).
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration time in minutes (default: 30).
- `BCRYPT_ROUNDS`: BCrypt cost factor/rounds for password hashing (default: 14).
- `BACKEND_CORS_ORIGINS`: Allowed origins for CORS (default: ["http://localhost:3000"]).
- `ENVIRONMENT`: Sets the environment mode (`production` or `development`), affecting logging format (default: development).
  - `development`: Human-readable logs for easier debugging
  - `production`: JSON-structured logs for machine parsing and log aggregation systems
- `LOG_LEVEL`: Controls logging verbosity (default: INFO).
  - `DEBUG`: Most verbose, shows all messages including detailed debugging information
  - `INFO`: Shows informational messages, warnings, errors, and critical issues
  - `WARNING`: Shows only warnings, errors, and critical issues
  - `ERROR`: Shows only errors and critical issues
  - `CRITICAL`: Shows only critical issues

## Development

### Requirements

- Python 3.13+
- uv package manager (for dependency management)
- MySQL 5.7+ (for both Prelude and Prebetter databases)

### Development Tools

- **Ruff**: Used for linting and code formatting.
- **PyTest**: Used for running tests.
- **Coverage**: Used for test coverage reporting.

### Development Commands

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

The test suite includes:

- API endpoint functionality tests.
- Data validation tests.
- Filtering and pagination tests.
- Timeline and statistics tests.
- Edge case handling tests.

## Performance Features

- **Optimized Database Queries:** Uses efficient joins with aliases, separate count queries, distinct selections, and proper indexing on key fields.
- **Efficient Payload Handling:** Preserves raw payload data and provides two representations (readable and original) for analysis.
- **Error Handling:** Provides specific error messages and robust exception handling.
- **Database Connection Pooling:** Managed via SQLAlchemy's connection pooling.
- **Asynchronous Request Handling:** Endpoints are defined as asynchronous functions for improved performance.
- **Query Optimization:** Implements progressive filtering from most to least selective for better query planning.
- **Index-Friendly Queries:** Designed to utilize database indexes effectively.
- **Timezone-Aware Date Handling:** Ensures consistent timezone handling in date filtering.

## Security Features

- **JWT Authentication:** Secure token-based authentication system.
- **Password Hashing:** Secure password storage using bcrypt hashing.
- **Role-Based Access Control:** Superuser and regular user permissions.
- **Input Validation:** Comprehensive validation for user data.
- **Unique Constraints:** Enforcement of username and email uniqueness.
- **Last Superuser Protection:** Prevents deletion of the last superuser.
- **Secure Key Generation:** Uses Python's secrets module for cryptographically secure key generation.
- **Request Tracking:** Unique request IDs for security audit trails.
- **Exception Handling:** Prevents information leakage in error responses.

## Middleware Architecture

The API implements a layered middleware architecture:

1. **CORS Middleware:** Handles Cross-Origin Resource Sharing with configurable origins.
2. **Request Tracking Middleware:** Generates and tracks request IDs, logs request details.
3. **Exception Handlers:** Provides consistent error responses with appropriate status codes.

## Data Models

### User Models

- **User Base:** Includes email, username, and an optional full name.
- **User Create:** Extends the base with a password field for user creation.
- **User Update:** Optional fields for updating user details.
- **User in DB:** Complete user model with system-generated fields (ID, created/updated timestamps, and superuser flag).

### Alert Models

- **Alert List Item:**
  - Identifiers: Alert ID (`id`) and message ID (`message_id`).
  - Timestamps: Creation (`created_at`) and detection (`detected_at`) times (with timezone support).
  - Classification & Severity: Classification text and severity level.
  - Network Information: Source and target IPv4 addresses.
  - Analyzer Details: Information about the analyzer that generated the alert.
- **Grouped Alert Detail:**
  - Groups alerts by source and target IPv4 addresses.
  - Provides aggregated counts, analyzer info, and latest detection time (`detected_at`).
- **Alert Detail:**
  - Full metadata including network, protocol, analyzer, process, references, services, and payload data. Fields include `id`, `created_at`, `detected_at`.
  - Byte-string payloads use a minimal structure in `additional_data` with two fields: `readable` (UTF-8 text) and `original` (base64 bytes).

### Export & Heartbeat Models

- **Export Alerts:**
  - Exports alert data in CSV format including all relevant fields.
- **Heartbeat Data:**
  - **Tree View:** Groups agents under hosts with details such as OS information, analyzer data (including `latest_heartbeat_at`), and current online/offline status.
  - **Timeline:** Aggregates heartbeat events over time with timestamps (`timestamp`) and agent identifiers.

### Health Models

- **Health Response:**
  - Overall system status: "healthy", "degraded", or "unhealthy"
  - Database connection availability for both Prelude and Prebetter
  - API uptime in seconds
  - Current server timestamp
