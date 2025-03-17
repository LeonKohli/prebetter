# Prelude SIEM API

A FastAPI-based REST API for accessing Prelude IDS/SIEM data with user management and authentication. This API provides comprehensive access to security alerts and related information from your Prelude SIEM system.

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
- **Payload Access:** View full payload data with an option to truncate for efficiency.
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
│   └── query_builders.py  # Query building utilities
├── models/               
│   ├── prelude.py         # SQLAlchemy models for SIEM (reflected via automap)
│   └── users.py           # User models
├── schemas/              
│   ├── prelude.py         # SIEM Pydantic models
│   └── users.py           # User Pydantic models
├── services/             
│   └── users.py           # Business logic for user operations
└── main.py                # Application entry point and lifespan configuration
```

## Database Structure

The application uses two separate MySQL databases:

1. **Prelude Database**: Contains all SIEM/IDS data including alerts, heartbeats, and analyzer information. This database is treated as read-only by the API.

2. **Prebetter Database**: Contains user management data. This database is managed by the API for user authentication and authorization.

The connection to these databases is handled through SQLAlchemy with:
- Connection pooling (pool size: 5, max overflow: 10)
- Connection validation via `pool_pre_ping`
- Separate session factories for each database

## Setup

1. **Clone the repository**

2. **Create a Virtual Environment:**

   ```bash
   uv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**

   ```bash
   uv add -r requirements.txt
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

5. **Import the Prelude Database (if needed for testing and development):**

   ```bash
   gunzip < prelude.sql.gz | mysql -u root -p prelude
   ```

6. **Start the API Server:**

   ```bash
   fastapi dev
   ```

## API Endpoints

### Authentication & User Management

- **Login:** `POST /api/v1/auth/token`
  - Request body: Form data with username and password.
  - Returns: JWT access token.

- **Current User:** `GET /api/v1/auth/users/me`
  - Returns: Current authenticated user's details.

- **Users (Superuser Only):**
  - **List Users:** `GET /api/v1/users/`
    - Supports pagination with `skip` and `limit` parameters.
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
    - `sort_by`: Sort field (`detect_time`, `create_time`, `severity`, `classification`, `source_ip`, `target_ip`, `analyzer`, `alert_id`)
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
  - **Query Parameter:**
    - `truncate_payload`: Boolean flag to truncate the payload data (default: false).
  - Returns: Detailed alert information including network, analyzer, and (optionally truncated) payload data.

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
  - Returns: A streaming CSV file containing alert data with a header row.

### Heartbeat Monitoring

- **Heartbeats Tree View:** `GET /api/v1/heartbeats/tree`
  - Returns: A JSON tree view of hosts and their associated agents, including:
    - Host OS information.
    - List of agents with details such as analyzer name, model, version, class, last heartbeat timestamp, and online/offline status.

- **Heartbeats Timeline:** `GET /api/v1/heartbeats/timeline`
  - **Query Parameters:**
    - `hours`: Number of past hours to include in the timeline (default: 24, min: 1, max: 168).
    - `page`: Page number (default: 1).
    - `page_size`: Items per page (default: 100, min: 1, max: 1000).
  - Returns: Timeline data of heartbeat events with agent name, node details, timestamp, and model.

- **Heartbeats Status:** `GET /api/v1/heartbeats/status`
  - **Query Parameters:**
    - `days`: Number of days to look back (default: 1, min: 1, max: 30).
    - `group_by_host`: Boolean flag to group results by host (default: false).
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
  - Returns: Overall statistics including total alerts, distribution by severity, classification, analyzer, and top source/target IP addresses.

### Reference Data

- **Classifications:** `GET /api/v1/classifications`
- **Severities:** `GET /api/v1/severities`
- **Analyzers:** `GET /api/v1/analyzers`

## Documentation

- **Interactive API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative API Documentation (ReDoc):** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Environment Variables

- `MYSQL_USER`: MySQL username.
- `MYSQL_PASSWORD`: MySQL password.
- `MYSQL_HOST`: MySQL host (default: localhost).
- `MYSQL_PORT`: MySQL port (default: 3306).
- `MYSQL_PRELUDE_DB`: Name of the Prelude database (default: prelude).
- `MYSQL_PREBETTER_DB`: Name of the Prebetter database (default: prebetter).
- `SECRET_KEY`: Secret key for JWT token generation (required).
- `JWT_SECRET_KEY`: Secret key specifically for JWT (default: uses `SECRET_KEY`).
- `JWT_ALGORITHM`: Algorithm used for JWT (default: HS256).
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration time in minutes (default: 30).
- `BACKEND_CORS_ORIGINS`: Allowed origins for CORS (default: ["*"]).

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
uv run pytest --cov=app

# Run linter
ruff check .

# Format code
ruff format .
```

## Testing

Run the test suite using [pytest](https://docs.pytest.org/):

```bash
# Optionally set PYTHONPATH to include the project root
export PYTHONPATH=$PYTHONPATH:$(pwd)
pytest tests/
```

The test suite includes:

- API endpoint functionality tests.
- Data validation tests.
- Filtering and pagination tests.
- Timeline and statistics tests.
- Edge case handling tests.

## Performance Features

- **Optimized Database Queries:** Uses efficient joins with aliases, separate count queries, distinct selections, and proper indexing on key fields.
- **Efficient Payload Handling:** Supports optional payload truncation.
- **Error Handling:** Provides specific error messages and robust exception handling.
- **Database Connection Pooling:** Managed via SQLAlchemy's connection pooling.
- **Asynchronous Request Handling:** Endpoints are defined as asynchronous functions for improved performance.

## Security Features

- **JWT Authentication:** Secure token-based authentication system.
- **Password Hashing:** Secure password storage using hashing.
- **Role-Based Access Control:** Superuser and regular user permissions.
- **Input Validation:** Comprehensive validation for user data.
- **Unique Constraints:** Enforcement of username and email uniqueness.
- **Last Superuser Protection:** Prevents deletion of the last superuser.

## Data Models

### User Models

- **User Base:** Includes email, username, and an optional full name.
- **User Create:** Extends the base with a password field for user creation.
- **User Update:** Optional fields for updating user details.
- **User in DB:** Complete user model with system-generated fields (ID, created/updated timestamps, and superuser flag).

### Alert Models

- **Alert List Item:**
  - Identifiers: Alert ID and message ID.
  - Timestamps: Creation and detection times (with timezone support).
  - Classification & Severity: Classification text and severity level.
  - Network Information: Source and target IPv4 addresses.
  - Analyzer Details: Information about the analyzer that generated the alert.
- **Grouped Alert:**
  - Groups alerts by source and target IPv4 addresses.
  - Provides aggregated counts and a breakdown of classifications.
- **Alert Detail:**
  - Full metadata including network, protocol, analyzer, process, references, services, and payload data.
  - Optional truncation for large payloads.

### Export & Heartbeat Models

- **Export Alerts:**
  - Exports alert data in CSV format including all relevant fields.
- **Heartbeat Data:**
  - **Tree View:** Groups agents under hosts with details such as OS information, analyzer data, and current online/offline status.
  - **Timeline:** Aggregates heartbeat events over time with timestamps and agent identifiers.
