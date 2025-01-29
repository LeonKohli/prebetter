# Prelude SIEM API

A FastAPI-based REST API for accessing Prelude IDS/SIEM data in read-only mode. This API provides comprehensive access to security alerts and related information from your Prelude SIEM system.

## Features

- **Alert Management**
  - Paginated alerts listing with rich filtering options
  - Detailed alert information including source, target, and analyzer details
  - Alert grouping by source and target IPs
  - Full payload access with optional truncation

- **Advanced Filtering**
  - Date range filtering with timezone support
  - Severity and classification filtering
  - Source and target IP filtering
  - Analyzer-based filtering

- **Data Analysis**
  - Statistical summaries of alerts
  - Severity distribution analysis
  - Top classifications and source IPs
  - Timeline visualization with customizable time frames

- **Logging & Monitoring**
  - Structured request logging with timing information
  - Separate access and error logs
  - Log rotation with size limits
  - Request tracing with file and line numbers
  - Performance metrics tracking

## Project Structure

```
app/
├── api/                    # API implementation
│   ├── base.py            # Main router configuration
│   └── v1/
│       └── routes/        # API endpoint implementations
│           ├── alerts.py      # Alert management endpoints
│           ├── reference.py   # Reference data endpoints
│           └── statistics.py  # Statistics endpoints
├── core/                  # Core functionality
│   ├── config.py          # Environment & app configuration
│   └── logging.py         # Logging configuration
├── database/             # Database layer
│   └── config.py         # Database connection management
├── models/               # Database models
│   └── prelude.py        # SQLAlchemy models
├── schemas/              # API schemas
│   └── prelude.py        # Pydantic models
└── main.py              # Application entry point
```

## Setup

1. Clone the repository
2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and update with your database credentials:

```bash
cp .env.example .env
```

5. Import the Prelude database (if needed):

```bash
gunzip < prelude.sql.gz | mysql -u root -p prelude
```

6. Start the API server:

```bash
uvicorn app.main:app --reload
```

## API Endpoints

### Alert Management

- `GET /api/v1/alerts/`: List alerts with pagination and filtering
  - Query parameters:
    - `page`: Page number (default: 1)
    - `size`: Items per page (default: 10, max: 100)
    - `sort_by`: Sort field (detect_time, create_time, severity, classification, source_ip, target_ip, analyzer)
    - `sort_order`: Sort order (asc, desc)
    - `severity`: Filter by severity
    - `classification`: Filter by classification
    - `start_date`: Start date in ISO format
    - `end_date`: End date in ISO format
    - `source_ip`: Filter by source IP
    - `target_ip`: Filter by target IP
    - `analyzer_model`: Filter by analyzer model

- `GET /api/v1/alerts/groups`: List alerts grouped by source and target IPs
  - Supports the same query parameters as the alerts listing endpoint

- `GET /api/v1/alerts/{alert_id}`: Get detailed alert information
  - Query parameters:
    - `truncate_payload`: Whether to truncate payload data (default: false)

### Statistics and Analysis

- `GET /api/v1/statistics/summary`: Get alert statistics summary
  - Query parameters:
    - `time_range`: Time range in hours to analyze (default: 24)

- `GET /api/v1/statistics/timeline`: Get alert timeline data
  - Query parameters:
    - `time_frame`: Grouping interval (hour, day, week, month)
    - `start_date`: Start date for analysis
    - `end_date`: End date for analysis
    - `severity`: Filter by severity
    - `classification`: Filter by classification

### Reference Data

- `GET /api/v1/classifications`: Get unique classification texts
- `GET /api/v1/severities`: Get unique impact severities
- `GET /api/v1/analyzers`: Get unique analyzer names

## Documentation

- Interactive API documentation: <http://localhost:8000/docs>
- Alternative API documentation: <http://localhost:8000/redoc>

## Environment Variables

- `MYSQL_USER`: MySQL username
- `MYSQL_PASSWORD`: MySQL password
- `MYSQL_HOST`: MySQL host (default: localhost)
- `MYSQL_PORT`: MySQL port (default: 3306)
- `MYSQL_DB`: MySQL database name (default: prelude)
- `LOG_LEVEL`: Logging level (default: INFO)

## Logging

The API uses a comprehensive logging system with the following features:

### Log Files
- `logs/app.log`: Main application logs (rotated, max 10MB)
- `logs/error.log`: Error-level logs only (rotated, max 10MB)
- `logs/access.log`: API request logs with timing (rotated, max 10MB)

### Log Format
- Console: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- File: `%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(pathname)s:%(lineno)d]`

### Request Logging
Each API request is logged with:
- Timestamp
- HTTP method
- URL
- Status code
- Response time
- Client IP
- User agent

## Testing

Run the test suite:

```bash
# Set PYTHONPATH to include the project root
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run tests
pytest tests/
```

The test suite includes:

- API endpoint functionality tests
- Data validation tests
- Filtering and pagination tests
- Timeline and statistics tests

## Performance Features

- Optimized database queries with proper indexing
- Efficient joins and subqueries
- Pagination to handle large datasets
- Optional payload truncation
- Proper database connection pooling
- Request timing metrics

## Security Notes

- This is a read-only API to ensure data safety
- CORS is configured but should be restricted in production
- Database credentials should be properly secured
- Consider implementing rate limiting for production use
