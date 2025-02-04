# Prelude SIEM API

A FastAPI-based REST API for accessing Prelude IDS/SIEM data with user management and authentication. This API provides comprehensive access to security alerts and related information from your Prelude SIEM system.

## Features

### User Management & Authentication
- **User Authentication:** JWT-based authentication system
- **Role-Based Access:** Superuser and regular user roles
- **User Operations:** 
  - Create/Update/Delete users (superuser only)
  - Password management (change/reset)
  - Email and username validation
  - Pagination for user listing
- **Concurrent Operation Handling:** Protection against race conditions in user operations

### Alert Management
- **Paginated Alerts Listing:** Browse alerts with rich filtering options.
- **Detailed Alert Information:** Retrieve comprehensive details including source, target, and analyzer information.
- **Alert Grouping:** Group alerts by source and target IP addresses.
- **Payload Access:** View full payload data with an option to truncate for efficiency.
- **Multi-Format Support:** Handles multiple alert formats and protocols.

### Advanced Filtering
- **Date Range Filtering:** Filter alerts by start and end dates (ISO format) with timezone support.
- **Severity & Classification Filtering:** Narrow down alerts by severity level and partial classification text.
- **IP-Based Filtering:** Filter by exact source and target IP addresses.
- **Analyzer Filtering:** Filter alerts by analyzer model.
- **Sorting Options:** Multiple fields available for sorting (e.g., detect time, create time, severity, etc.).

### Data Analysis
- **Timeline Visualization:** Generate timelines based on hourly, daily, weekly, or monthly intervals.
- **Statistical Summaries:** View total alert counts and distributions by severity, classification, and analyzer.
- **Top Metrics:** Identify top classifications and source/target IPs.
- **Grouped Data:** Get alerts grouped by various metrics for an aggregated view.

## Project Structure

```
app/
├── api/                    # API implementation
│   ├── base.py            # Main router configuration
│   └── v1/
│       └── routes/        # API endpoint implementations
│           ├── alerts.py      # Alert management endpoints
│           ├── auth.py        # Authentication endpoints
│           ├── users.py       # User management endpoints
│           ├── reference.py   # Reference data endpoints
│           └── statistics.py  # Statistics endpoints
├── core/                  # Core functionality
│   ├── config.py          # Environment & app configuration
│   ├── security.py        # Authentication & security utilities
│   └── logging.py         # Logging configuration
├── database/             # Database layer
│   ├── config.py         # Database connection management
│   └── init_db.py        # Database initialization
├── models/               # Database models
│   ├── prelude.py        # SQLAlchemy models for SIEM
│   └── users.py          # User models
├── schemas/              # API schemas
│   ├── prelude.py        # SIEM Pydantic models
│   └── users.py          # User Pydantic models
├── services/            # Business logic
│   └── users.py         # User service layer
└── main.py              # Application entry point
```

## Setup

1. **Clone the repository**

2. **Create a Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   - Copy the example file and update your credentials:
     ```bash
     cp .env.example .env
     ```
   - Required variables:
     - Database credentials (as before)
     - `SECRET_KEY`: For JWT token generation
     - `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time

5. **Import the Prelude Database (if needed):**
   ```bash
   gunzip < prelude.sql.gz | mysql -u root -p prelude
   ```

6. **Start the API Server:**
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

### Authentication & User Management

- **Login**: `POST /api/v1/auth/token`
  - Request body: username and password
  - Returns: JWT access token

- **Current User**: `GET /api/v1/auth/users/me`
  - Returns current authenticated user's details

- **Users (Superuser Only)**:
  - List: `GET /api/v1/users/`
    - Supports pagination with `skip` and `limit` parameters
  - Create: `POST /api/v1/users/`
  - Get: `GET /api/v1/users/{user_id}`
  - Update: `PUT /api/v1/users/{user_id}`
  - Delete: `DELETE /api/v1/users/{user_id}`

- **Password Management**:
  - Change Password: `POST /api/v1/users/change-password`
  - Reset Password (Superuser): `POST /api/v1/users/{user_id}/reset-password`

### Alert Management

- **List Alerts**: `GET /api/v1/alerts/`
    
    - **Query Parameters:**
        - `page`: Page number (default: 1)
        - `size`: Items per page (default: 10, max: 100)
        - `sort_by`: Sort field (`detect_time`, `create_time`, `severity`, `classification`, `source_ip`, `target_ip`, `analyzer`, `alert_id`)
        - `sort_order`: Sort order (`asc`, `desc`)
        - `severity`: Filter by severity
        - `classification`: Filter by classification text (partial match supported)
        - `start_date`: Start date in ISO format
        - `end_date`: End date in ISO format
        - `source_ip`: Filter by source IP (exact match)
        - `target_ip`: Filter by target IP (exact match)
        - `analyzer_model`: Filter by analyzer model
- **Grouped Alerts**: `GET /api/v1/alerts/groups`
    
    - Supports the same query parameters as the alerts listing endpoint.
    - Groups alerts by source and target IP addresses and provides a classification breakdown per group.
- **Alert Detail**: `GET /api/v1/alerts/{alert_id}`
    
    - **Query Parameter:**
        - `truncate_payload`: Boolean flag to truncate the payload data (default: false).
    - Returns detailed alert information including network, TCP/IP, service, and full (or truncated) payload data.

### Statistics and Analysis

- **Timeline Data**: `GET /api/v1/statistics/timeline`
    
    - **Query Parameters:**
        - `time_frame`: Grouping interval (`hour`, `day`, `week`, `month`)
        - `start_date`: Start date for analysis (optional)
        - `end_date`: End date for analysis (optional)
        - `severity`: Filter by severity (optional)
        - `classification`: Filter by classification (optional)
        - `analyzer_name`: Filter by analyzer name (optional)
- **Statistics Summary**: `GET /api/v1/statistics/summary`
    
    - **Query Parameter:**
        - `time_range`: Time range in hours to analyze (default: 24, min: 1, max: 720)

### Reference Data

- **Classifications**: `GET /api/v1/classifications`
- **Severities**: `GET /api/v1/severities`
- **Analyzers**: `GET /api/v1/analyzers`

## Documentation

- **Interactive API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative API Documentation (ReDoc):** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Environment Variables

- `MYSQL_USER`: MySQL username
- `MYSQL_PASSWORD`: MySQL password
- `MYSQL_HOST`: MySQL host (default: localhost)
- `MYSQL_PORT`: MySQL port (default: 3306)
- `MYSQL_DB`: MySQL database name (default: prelude)
- `SECRET_KEY`: Secret key for JWT token generation
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration time in minutes

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
- Reference data validation.
- Authentication and authorization tests
- User management tests
- Edge case handling for user operations
- Concurrent user operation tests

## Performance Features

- **Optimized Database Queries:** Uses efficient joins with aliases, separate count queries, distinct selections, and proper indexing on key fields.
- **Efficient Payload Handling:** Supports optional payload truncation.
- **Error Handling:** Provides specific error messages and robust exception handling.
- **Database Connection Pooling:** Managed via SQLAlchemy's connection pooling.
- **Asynchronous Request Handling:** Endpoints are defined as asynchronous functions for improved performance.

## Security Features

- **JWT Authentication:** Secure token-based authentication system
- **Password Hashing:** Secure password storage using hashing
- **Role-Based Access Control:** Superuser and regular user permissions
- **Input Validation:** Comprehensive validation for user data
- **Unique Constraints:** Username and email uniqueness enforcement
- **Last Superuser Protection:** Prevents deletion of the last superuser

## Data Models

### User Models
- **User Base:** Email, username, and optional full name
- **User Create:** Includes password for user creation
- **User Update:** Optional fields for updating user details
- **User in DB:** Complete user model with system fields

### Alert List Item

- **Identifiers:** Alert ID and message ID.
- **Timestamps:** Creation and detection times with timezone information.
- **Classification & Severity:** Classification text and severity level.
- **Network Information:** Source and target IPv4 addresses.
- **Analyzer Details:** Information about the analyzer that generated the alert.

### Grouped Alert

- **Grouping:** Alerts are grouped by source and target IPv4 addresses.
- **Metrics:** Total alert count, classification breakdown, analyzer distribution, and latest detection times.

### Alert Detail

- **Metadata:** Full alert metadata.
- **Network & Protocol Data:** Detailed network information (IPv4/IPv6) and TCP/IP protocol details.
- **Analyzer & Process Information:** Analyzer details with associated node and process data.
- **References & Services:** Lists of reference URLs and service details.
- **Payload Data:** Decoded payload data, with optional truncation for large payloads.