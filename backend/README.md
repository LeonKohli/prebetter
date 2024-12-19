# Prelude SIEM API

A FastAPI-based REST API for accessing Prelude IDS/SIEM data in read-only mode. This API provides comprehensive access to security alerts and related information from your Prelude SIEM system.

## Features

- **Alert Management**
  - Paginated alerts listing with rich filtering options
  - Detailed alert information including source, target, and analyzer details
  - Full payload access with optional truncation
  - Timeline visualization of alert frequency

- **Advanced Filtering**
  - Date range filtering with timezone support
  - Severity and classification filtering
  - Source and target IP filtering
  - Analyzer-based filtering

- **Data Analysis**
  - Statistical summaries of alerts
  - Severity distribution analysis
  - Top classifications and source IPs
  - Customizable time-based analysis

- **Performance Features**
  - Optimized database queries
  - Configurable pagination
  - Efficient data loading
  - Response caching support

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
    - `size`: Items per page (default: 20, max: 100)
    - `start_date`: Start date in ISO format with timezone
    - `end_date`: End date in ISO format with timezone
    - `severity`: Filter by severity
    - `classification`: Filter by classification
    - `source_ip`: Filter by source IP
    - `target_ip`: Filter by target IP
    - `analyzer_name`: Filter by analyzer name
    - `sort_by`: Sort field (detect_time, create_time, severity, classification)
    - `sort_order`: Sort order (asc, desc)

- `GET /api/v1/alerts/{alert_id}`: Get detailed alert information
  - Query parameters:
    - `truncate_payload`: Whether to truncate payload data (default: false)

### Statistics and Analysis
- `GET /api/v1/statistics/summary`: Get alert statistics summary
  - Query parameters:
    - `time_range`: Time range in hours to analyze (default: 24)

- `GET /api/v1/timeline`: Get alert timeline data
  - Query parameters:
    - `time_frame`: Grouping interval (hour, day, week, month)
    - `start_date`: Start date for analysis
    - `end_date`: End date for analysis
    - `severity`: Filter by severity
    - `classification`: Filter by classification
    - `analyzer_name`: Filter by analyzer

### Reference Data
- `GET /api/v1/classifications/`: Get unique classification texts
- `GET /api/v1/impacts/severities/`: Get unique impact severities
- `GET /api/v1/analyzers/`: Get unique analyzer names

## Documentation

- Interactive API documentation: http://localhost:8000/docs
- Alternative API documentation: http://localhost:8000/redoc

## Environment Variables

- `MYSQL_USER`: MySQL username
- `MYSQL_PASSWORD`: MySQL password
- `MYSQL_HOST`: MySQL host (default: localhost)
- `MYSQL_PORT`: MySQL port (default: 3306)
- `MYSQL_DB`: MySQL database name (default: prelude)

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

## Performance Considerations

- The API uses optimized database queries to minimize response times
- Large payloads can be truncated to improve performance
- Timeline queries are optimized based on the selected time frame
- Database connections are properly managed and pooled

## Security Notes

- This is a read-only API to ensure data safety
- CORS is configured but should be restricted in production
- Database credentials should be properly secured
- Consider implementing rate limiting for production use

