# Prebetter

A web dashboard for [Prelude IDS](https://www.prelude-siem.org/). Browse, filter, and analyze security alerts through a modern interface instead of Prelude's default tooling.

## What is this?

Prebetter connects directly to Prelude's MySQL database and gives you a web UI on top of it. You get alert filtering, timeline stats, heartbeat monitoring, CSV export, and user management with role-based access.

Prelude IDS is an open-source intrusion detection system. Its default interfaces are... not great. This project exists because we needed something better.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Browser    │────▶│   Frontend   │────▶│    Backend API   │
│              │     │   (Nuxt 4)   │     │    (FastAPI)     │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                                          ┌────────┴────────┐
                                          │                 │
                                    ┌─────▼─────┐   ┌──────▼──────┐
                                    │ Prelude DB │   │ Prebetter DB│
                                    │ (read-only)│   │  (users)    │
                                    └───────────┘   └─────────────┘
```

The frontend is a Nuxt 4 / Vue 3 SPA (shadcn-vue, Tailwind CSS, dark/light mode). The backend is a FastAPI REST API with JWT auth. Two MySQL databases: Prelude's existing one (read-only) and a separate one for user management.

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 20+
- MySQL 5.7+
- uv (Python package manager)
- Bun (JavaScript package manager)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/LeonKohli/prebetter.git
   cd prebetter
   ```

2. **Set up the backend:**
   ```bash
   cd backend
   uv sync
   cp .env.example .env
   # Edit .env with your database credentials
   fastapi dev
   ```

3. **Set up the frontend:**
   ```bash
   cd frontend
   bun install
   bun run dev
   ```

4. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/api/v1/docs

## Features

- Alert browsing with filtering by severity, classification, IP, date range
- Alert grouping by source/target IP pairs
- Heartbeat monitoring (which agents are alive, which dropped off)
- Timeline and summary statistics
- CSV export
- JWT auth with superuser/regular user roles
- Dark/light mode

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Nuxt 4, Vue 3, TypeScript, Tailwind CSS v4, shadcn-vue |
| Backend | FastAPI, SQLAlchemy, Pydantic, PyJWT |
| Database | MySQL 5.7+ (Prelude DB + user management DB) |
| Package Managers | [uv](https://docs.astral.sh/uv/) (Python), [Bun](https://bun.sh/) (JS) |

## Documentation

- [Backend README](./backend/README.md) — API endpoints, database schema, setup details
- [Frontend README](./frontend/README.md) — component structure, auth flow, styling
- [API docs](http://localhost:8000/api/v1/docs) — interactive Swagger UI (when running)

## Motivation

Prelude IDS does its job well, but the existing tools for actually looking at the data it collects haven't kept up. We needed a way to quickly browse alerts, see what's happening across our network, and not fight the UI while doing it. So we built one.

## Contributing

1. Fork the repository
2. Create a feature branch from `dev`
3. Test thoroughly
4. Submit a pull request

## License

[GPL-3.0](./LICENSE)
