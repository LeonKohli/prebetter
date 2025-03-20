# Prelude SIEM Dashboard

A modern, comprehensive Security Information and Event Management (SIEM) dashboard that combines a FastAPI backend with a Nuxt.js frontend to provide real-time monitoring, analysis, and management of security alerts.

## Project Overview

This project consists of two main components:

1. **Backend API (FastAPI)**: A performant REST API for accessing Prelude IDS/SIEM data with user management and authentication. See the [Backend README](./backend/README.md) for more details.
2. **Frontend Dashboard (Nuxt.js)**: A responsive, user-friendly dashboard for visualizing and interacting with security alerts. See the [Frontend README](./frontend/README.md) for more details.

## Features

### Backend Features

- **User Management & Authentication**: JWT-based authentication with role-based access control
- **Alert Management**: Filter, sort, and export security alerts
- **Heartbeat Monitoring**: Monitor the status of security agents across your network
- **Statistical Analysis**: Generate timelines and statistical summaries of security data
- **Export Functionality**: Export alerts in CSV format for further analysis

### Frontend Features

- **Responsive Dashboard**: Modern UI that works on desktop and mobile
- **Real-time Visualization**: Interactive charts and graphs for security data
- **Dark/Light Mode**: Theme support for different environments
- **Data Tables**: Sortable, filterable tables for security alerts
- **Timeline Views**: Chronological view of security events

## Getting Started

### Prerequisites

- Python 3.x+
- Node.js 20+
- MySQL 5.7+
- uv package manager (for Python dependencies)
- bun or npm (for JavaScript dependencies)

### Installation

#### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   uv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   uv add -r requirements.txt # Or use uv sync
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and other settings
   ```

5. Start the API server:
   ```bash
   fastapi dev
   ```

   The API will be available at http://localhost:8000 with documentation at http://localhost:8000/docs

#### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   bun install
   # or
   npm install
   ```

3. Start the development server:
   ```bash
   bun dev
   # or
   npm run dev
   ```

   The frontend will be available at http://localhost:3000

## Project Structure

```
prelude-siem/
├── backend/                  # FastAPI Backend
│   ├── app/                  # Application code
│   │   ├── api/              # API endpoints
│   │   ├── core/             # Core functionality
│   │   ├── database/         # Database configuration
│   │   ├── models/           # Data models
│   │   ├── schemas/          # Pydantic schemas
│   │   └── services/         # Business logic
│   ├── tests/                # Test suite
│   └── requirements.txt      # Python dependencies
├── frontend/                 # Nuxt.js Frontend
│   ├── app/                  # Application code
│   │   ├── components/       # Reusable components
│   │   ├── composables/      # Shared state and logic
│   │   ├── layouts/          # Page layouts
│   │   └── pages/            # Application pages
│   └── package.json          # JavaScript dependencies
└── README.md                 # Project documentation
```

## Database Structure

The application uses two separate MySQL databases:

1. **Prelude Database**: Contains all SIEM/IDS data including alerts, heartbeats, and analyzer information. This database is treated as read-only by the API.
2. **Prebetter Database**: Contains user management data. This database is managed by the API for user authentication and authorization.

## API Documentation

- Interactive API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative API Documentation (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Development

### Backend Development

```bash
cd backend

# Run tests
uv run pytest --cov=app

# Run linter
ruff check .

# Format code
ruff format .
```

### Frontend Development

```bash
cd frontend

# Run development server
bun dev

# Build for production
bun build

# Preview production build
bun preview
```

## Environment Variables

### Backend

- `MYSQL_USER`: MySQL username
- `MYSQL_PASSWORD`: MySQL password
- `MYSQL_HOST`: MySQL host (default: localhost)
- `MYSQL_PORT`: MySQL port (default: 3306)
- `MYSQL_PRELUDE_DB`: Name of the Prelude database (default: prelude)
- `MYSQL_PREBETTER_DB`: Name of the Prebetter database (default: prebetter)
- `SECRET_KEY`: Secret key for JWT token generation
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration time in minutes (default: 30)
- `BACKEND_CORS_ORIGINS`: Allowed origins for CORS (default: ["*"])

### Frontend

- `NUXT_PUBLIC_API_BASE`: Base URL of the backend API

## License

This project is licensed under the GPL-3.0 License - see the LICENSE file for details.
