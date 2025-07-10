# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Prebetter** is a modern Security Information and Event Management (SIEM) dashboard that provides real-time security alert monitoring and analysis through a web-based interface.

## Architecture Overview

- **Backend**: FastAPI REST API serving Prelude IDS/SIEM data with JWT authentication
- **Frontend**: Nuxt 3 SPA with server-side rendering and session-based authentication
- **Database**: Dual MySQL system (Prelude DB for SIEM data, Prebetter DB for users)
- **Authentication**: JWT tokens stored in secure server-side sessions

## Project Structure

```
prebetter/
├── backend/          # FastAPI backend API
├── frontend/         # Nuxt 3 frontend application
└── CLAUDE.md        # This file
```

## Key Architectural Decisions

1. **Authentication Flow**: 
   - Backend issues JWT tokens
   - Frontend stores tokens in secure server-side sessions only
   - All API calls proxied through frontend server for token injection
   - 30-minute session timeout synchronized between systems

2. **Security First**:
   - No client-side token storage
   - HttpOnly session cookies
   - Server-side API proxy pattern
   - Automatic 401 handling with redirects

3. **Developer Experience**:
   - Type-safe end-to-end with TypeScript
   - Auto-imports in frontend
   - Hot-reload development
   - Comprehensive error handling

## Quick Start

```bash
# Backend
cd backend
uv sync
fastapi dev

# Frontend (separate terminal)
cd frontend
bun install
bun run dev
```

## Component-Specific Guidance

For detailed implementation guidance, refer to:
- **[Frontend CLAUDE.md](frontend/CLAUDE.md)** - Nuxt 3, Vue 3, UI patterns
- **[Backend CLAUDE.md](backend/CLAUDE.md)** - FastAPI, SQLAlchemy, API patterns

## Common Patterns

### Authentication Flow
1. User submits credentials to frontend
2. Frontend calls backend `/api/v1/auth/token`
3. Backend validates and returns JWT token
4. Frontend stores token in secure server-side session
5. All subsequent API calls include token via server proxy
6. Session expires after 30 minutes (synchronized)

### Error Handling
- Backend returns standardized error responses
- Frontend handles 401s with automatic redirects
- User-friendly error messages displayed
- Network errors handled gracefully

## Environment Setup

Both components require environment configuration:

### Backend
- MySQL connection details
- JWT secret key
- CORS origins configuration

### Frontend  
- Session password (32+ characters)
- API base URL configuration
- Session timeout settings

See component-specific CLAUDE.md files for detailed configuration.

## Security Architecture

- **Zero client-side token exposure**: All JWT tokens stored server-side only
- **Session-based authentication**: Using encrypted httpOnly cookies
- **API proxy pattern**: Frontend server handles all backend communication
- **Synchronized expiration**: 30-minute timeout on both systems
- **Automatic security responses**: 401 errors trigger immediate session cleanup

## Development Workflow

1. **Backend First**: Start the FastAPI backend for API availability
2. **Frontend Development**: Use Nuxt dev server with hot-reload
3. **Type Safety**: TypeScript enforced end-to-end
4. **Testing**: Component-specific test suites

## API Documentation

When backend is running:
- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`
- OpenAPI Schema: `http://localhost:8000/api/v1/openapi.json`

## Technology Requirements

- **Python**: 3.13+ (backend)
- **Node.js**: 18+ (frontend)
- **Package Managers**: `uv` for Python, `bun` for JavaScript
- **MySQL**: 5.7+ for dual database system

## Important Conventions

- **Git Commits**: Never include "Co-Authored-By: Claude" in commit messages
- **Functional Programming**: Preferred over OOP, especially in frontend
- **Type Safety**: Enforce TypeScript and Python type hints
- **Component Isolation**: Backend and frontend are independently deployable