# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 CRITICAL: Git Commit Rules 🚨

**NEVER EVER include "Co-Authored-By: Claude" in commit messages. This is ABSOLUTELY FORBIDDEN.**
**NEVER EVER include "Co-Authored-By: Claude" in commit messages. This is ABSOLUTELY FORBIDDEN.**
**NEVER EVER include "Co-Authored-By: Claude" in commit messages. This is ABSOLUTELY FORBIDDEN.**

## Project Overview

**Prebetter** is a modern Intrusion Detection System (IDS) dashboard that provides real-time security alert monitoring and analysis through a web-based interface for Prelude IDS.

## Architecture Overview

- **Backend**: FastAPI REST API serving Prelude IDS data with JWT authentication
- **Frontend**: Nuxt 3 SPA with server-side rendering and session-based authentication
- **Database**: Dual MySQL system (Prelude DB for IDS data, Prebetter DB for users)
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
   - Backend issues JWT access + refresh token pairs
   - Frontend stores tokens in secure server-side sessions only
   - All API calls proxied through frontend server for token injection
   - Access tokens: 15 minutes (auto-refreshed transparently)
   - Refresh tokens: 7 days (session lifetime)
   - Nuxt session: 7 days (synchronized with refresh token)

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
3. Backend validates and returns access + refresh token pair
4. Frontend stores both tokens in secure server-side session
5. All subsequent API calls include access token via server proxy
6. Access token auto-refreshes 2 minutes before expiry (transparent to user)
7. Session expires after 7 days (or when refresh token expires)

### Error Handling
- Backend returns standardized error responses
- Frontend handles 401s with automatic redirects
- User-friendly error messages displayed
- Network errors handled gracefully

## Environment Setup

Both components require environment configuration:

### Backend
- MySQL connection details
- `SECRET_KEY` - JWT signing key (32+ characters, NOT JWT_SECRET_KEY)
- `ACCESS_TOKEN_EXPIRE_MINUTES=15` - Short-lived access tokens
- `REFRESH_TOKEN_EXPIRE_DAYS=7` - Long-lived refresh tokens
- CORS origins configuration

### Frontend
- Session password (32+ characters)
- API base URL configuration
- Session maxAge: 7 days (synchronized with refresh token lifetime)

See component-specific CLAUDE.md files for detailed configuration.

## Security Architecture

- **Zero client-side token exposure**: All JWT tokens stored server-side only
- **Session-based authentication**: Using encrypted httpOnly cookies
- **API proxy pattern**: Frontend server handles all backend communication
- **Token type enforcement**: Refresh tokens rejected on protected endpoints
- **Automatic token refresh**: Access tokens refreshed transparently before expiry
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

## Known Issues & Limitations

### Security
1. **No Rate Limiting**: Login endpoint (`/api/v1/auth/token`) has no rate limiting
   - **Risk**: Vulnerable to brute force attacks
   - **Priority**: HIGH - Implement before production deployment
   - **Solution**: Add slowapi or similar rate limiting library

2. **No Token Revocation**: JWTs valid until expiration
   - Access tokens: 15 minutes (short window limits damage)
   - Refresh tokens: 7 days (server-side only, never exposed to client)
   - Logout only clears frontend session
   - **Mitigation**: Short access token window + server-side storage reduces risk

### Testing & CI/CD
1. **Tests Not Running in CI**: 112 backend tests exist but don't execute in GitHub Actions
   - **Priority**: URGENT - Enable pytest in CI pipeline
   - Current CI only runs Ruff linting

2. **Frontend Testing Gap**: Minimal test coverage (~5%)
   - Only utility functions tested
   - No component, page, or integration tests
   - **Priority**: HIGH - Add component tests

## Session & Token Management

### Token Lifetimes
- **Access Token**: `ACCESS_TOKEN_EXPIRE_MINUTES=15` (short-lived, auto-refreshed)
- **Refresh Token**: `REFRESH_TOKEN_EXPIRE_DAYS=7` (session lifetime)
- **Nuxt Session**: `maxAge: 7 * 24 * 60 * 60` (7 days, matches refresh token)

### Token Type Enforcement
- Access tokens have `"type": "access"` claim
- Refresh tokens have `"type": "refresh"` claim
- `get_current_user` rejects tokens without `type: access`
- `/refresh` endpoint rejects tokens without `type: refresh`

### Token Security
- JWT tokens stored server-side only (never exposed to client)
- Session cookies are httpOnly, secure (production), and encrypted
- `SECRET_KEY` environment variable used for JWT signing (NOT JWT_SECRET_KEY)