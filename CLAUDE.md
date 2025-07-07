# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Prebetter** is a modern Security Information and Event Management (SIEM) dashboard that combines:
- **Backend**: FastAPI-based REST API for accessing Prelude IDS/SIEM data with user management and authentication
- **Frontend**: Nuxt.js 3 dashboard for visualizing and interacting with security alerts

## Architecture Summary

### Backend (FastAPI)
- **Location**: `/backend`
- **Tech Stack**: Python 3.13+, FastAPI, SQLAlchemy 2.0, PyJWT, pytest, uv package manager
- **Databases**: Dual MySQL system (Prelude DB for SIEM data, Prebetter DB for users)
- **Authentication**: JWT-based with role-based access control
- **API Base URL**: `http://localhost:8000/api/v1`

### Frontend (Nuxt 3)
- **Location**: `/frontend`
- **Tech Stack**: Nuxt 3, Vue 3 (Composition API), shadcn-vue, Tailwind CSS v4, TypeScript, Bun
- **Key Features**: Responsive dashboard with dark/light mode, real-time data visualization

## Common Development Commands

### Backend Commands
```bash
cd backend

# Development
uvicorn app.main:app --reload  # Start dev server
fastapi dev                     # Alternative using FastAPI CLI

# Testing
pytest -v                       # Run all tests
pytest tests/test_alerts.py -v  # Run specific test
uv run pytest --cov            # Run with coverage

# Linting & Formatting
ruff check .                   # Check code
ruff check . --fix            # Fix auto-fixable issues
ruff format .                 # Format code

# Package Management (using uv)
uv sync                       # Install dependencies
uv add <package>             # Add new dependency
```

### Frontend Commands
```bash
cd frontend

# Development (using Bun - required)
bun run dev          # Start dev server (port 3000)
bun run typecheck    # Run type checking
bun run build        # Build for production
bun run preview      # Preview production build
bun run test         # Run tests with Vitest

# UI Components
bunx shadcn-vue@latest add <component-name>  # Add shadcn component
```

## Key API Endpoints

### Authentication
- `POST /api/v1/auth/token` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user info

### Core Endpoints
- `/api/v1/alerts/` - Security alerts with extensive filtering
- `/api/v1/statistics/timeline` - Alert timeline statistics
- `/api/v1/statistics/summary` - Summary statistics
- `/api/v1/heartbeats/status` - Agent status monitoring
- `/api/v1/heartbeats/tree` - Hierarchical view of agents
- `/api/v1/reference/classifications` - Alert classifications
- `/api/v1/reference/severities` - Alert severity levels
- `/api/v1/export/alerts/{format}` - Export alerts (CSV)

## Code Patterns & Best Practices

### Backend Patterns

#### Query Construction
```python
# Use query builders
query, models = build_alert_base_query(db)

# Apply standard filters
query = apply_standard_alert_filters(
    query=query,
    severity=severity,
    classification=classification,
    # ... other filters
)

# Apply sorting with string keys
sort_options = {
    "detect_time": DetectTime.time,
    "severity": Impact.severity,
}
query = apply_sorting(query, sort_by, sort_order, sort_options)

# Convert results
items = [alert_result_to_list_item(result) for result in results]
```

#### Performance Considerations
- Always limit query results: `query.limit(1000)`
- Use `.distinct()` to eliminate duplicates
- For exports, use generators and `yield_per()`
- Consider pagination for large datasets

### Frontend Patterns

#### Data Fetching
```typescript
// SSR-optimized requests
const { data, error, pending } = await useFetch('/api/v1/alerts', {
  baseURL: 'http://localhost:8000',
  headers: {
    Authorization: `Bearer ${token.value}`
  }
})
```

#### Component Development
- Use Composition API with TypeScript only
- No manual imports for Vue/Nuxt functions (auto-imported)
- Follow naming conventions:
  - **PascalCase**: Components (`AlertTable.vue`)
  - **camelCase**: Pages and functions (`alerts.vue`, `useAlerts`)
  - **use[Name]**: Composables (`useAuth`, `useAlerts`)

#### Styling
- Use inline Tailwind classes only - no @apply directives
- Always use predefined color variables:
  - `bg-background`, `text-foreground` (main content)
  - `bg-card`, `text-card-foreground` (cards)
  - `bg-primary`, `text-primary-foreground` (primary actions)
  - `bg-muted`, `text-muted-foreground` (subtle content)
  - `border-border`, `ring-ring` (borders and focus)

## Environment Configuration

### Backend (.env)
```env
# MySQL Connection
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_PRELUDE_DB=prelude
MYSQL_PREBETTER_DB=prebetter

# Security
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SECRET_KEY=your-secret-key

# Environment & Logging
ENVIRONMENT=development
LOG_LEVEL=INFO

# CORS
BACKEND_CORS_ORIGINS=["*"]
```

### Frontend Environment
- Configure API base URL in Nuxt config or environment variables

## Project Structure

```
prebetter/
├── backend/
│   ├── app/
│   │   ├── api/          # Route definitions
│   │   ├── core/         # Core utilities, config, security
│   │   ├── database/     # Database utilities, query builders
│   │   ├── middleware/   # CORS, exception handling
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Business logic layer
│   └── tests/            # Test suite
├── frontend/
│   ├── app/
│   │   ├── components/   # Vue components
│   │   │   └── ui/      # shadcn-vue UI components
│   │   ├── composables/  # Reusable composition functions
│   │   ├── layouts/      # Layout templates
│   │   ├── pages/        # File-based routing
│   │   └── utils/        # Utility functions
│   └── server/api/       # Server API endpoints (BFF pattern)
└── README.md

```

## Common Utilities

### Backend Utilities
- **Join Conditions**: Centralized in `database/config.py`
- **Query Helpers**: `apply_standard_alert_filters`, `apply_sorting`
- **Model Converters**: Functions in `database/models.py` for transforming query results
- **Datetime Handling**: Use `datetime_utils.ensure_timezone()` for timezone-aware operations

### Frontend Utilities
- **Icons**: Use `<Icon name="lucide:icon-name" />` from @nuxt/icon
- **State Management**: Create dedicated composables for each API domain
- **Error Handling**: 
  - Client: `throw createError('Error message')`
  - Server: `throw createError({ statusCode: 404, statusMessage: 'Not found' })`

## Security Considerations

- JWT tokens for authentication (consider httpOnly cookies for security)
- Password hashing with bcrypt
- Request tracking with unique IDs for audit trails
- Input validation on both frontend and backend
- Never expose sensitive information in client-side code
- Sanitize displayed alert data to prevent XSS

## Testing & Quality

### Backend Testing
- Use pytest with fixtures for database sessions
- Test coverage reporting with pytest-cov
- Integration tests for API endpoints

### Frontend Testing
- Vitest for unit and component testing
- Type checking with vue-tsc

### Code Quality
- Backend: ruff for linting and formatting
- Frontend: TypeScript for type safety
- Follow existing code patterns and conventions

## Performance Optimization

### Backend
- Connection pooling (pool_size=5, max_overflow=10)
- Query optimization with proper indexes
- Pagination for large datasets
- Batch processing for exports

### Frontend
- Lazy loading for below-fold content
- Cache reference data using `useState`
- Debounce search inputs and filters
- Virtual scrolling for large tables

## Documentation

- Backend API docs: `http://localhost:8000/api/v1/docs` (Swagger UI)
- Backend ReDoc: `http://localhost:8000/api/v1/redoc`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`

## Important Notes

- **Python Version**: 3.13+ required
- **Package Managers**: Use `uv` for Python, `bun` for JavaScript
- **Git Commits**: Never include "Co-Authored-By: Claude" in commit messages
- **No Classes**: Use functional programming patterns in frontend
- **Request IDs**: Every backend request gets a unique ID in `X-Request-ID` header