# Prelude SIEM API

A FastAPI-based REST API for accessing Prelude IDS/SIEM data in read-only mode.

## Features

- Read-only access to Prelude SIEM data
- Automatic table reflection using SQLAlchemy
- Paginated alerts listing
- Detailed alert information with related data
- Classification and severity statistics

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
5. Start the API server:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

- `GET /api/v1/alerts/`: List alerts with pagination
- `GET /api/v1/alerts/{alert_id}`: Get detailed information about a specific alert
- `GET /api/v1/classifications/`: Get unique classification texts
- `GET /api/v1/impacts/severities/`: Get unique impact severities

## Documentation

- Interactive API documentation: http://localhost:8000/docs
- Alternative API documentation: http://localhost:8000/redoc

## Environment Variables

- `MYSQL_USER`: MySQL username
- `MYSQL_PASSWORD`: MySQL password
- `MYSQL_HOST`: MySQL host (default: localhost)
- `MYSQL_PORT`: MySQL port (default: 3306)
- `MYSQL_DB`: MySQL database name (default: prelude) 