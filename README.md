# Prebetter - IDS Dashboard

A modern Intrusion Detection System (IDS) dashboard that provides a comprehensive interface for monitoring and analyzing security alerts from Prelude IDS.

## Overview

Prebetter consists of two main components working together:

- **Backend API**: FastAPI-based REST API that interfaces with Prelude databases
- **Frontend Dashboard**: Nuxt.js 3 application providing interactive visualizations

## Architecture

```
prebetter/
├── backend/          # FastAPI backend service
├── frontend/         # Nuxt.js frontend application  
├── CLAUDE.md        # AI assistant guidance
└── README.md        # This file
```

### Backend
- FastAPI with Python 3.13+
- Dual MySQL database system (Prelude + User management)
- JWT authentication with role-based access control
- Comprehensive API for alerts, statistics, and monitoring

### Frontend  
- Nuxt 3 with Vue 3 Composition API
- Modern UI with shadcn-vue components
- Real-time dashboards and data visualization
- Responsive design with dark/light mode support

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

- **Security Alert Management**: View, filter, and analyze security alerts
- **System Monitoring**: Real-time heartbeat monitoring of security agents
- **Statistical Analysis**: Timeline views and summary statistics
- **Data Export**: Export alerts in various formats for external analysis
- **User Management**: Secure authentication and role-based access control
- **Modern UI**: Responsive design with intuitive data visualization

## Documentation

- **Backend Documentation**: See [backend/README.md](./backend/README.md)
- **Frontend Documentation**: See [frontend/README.md](./frontend/README.md)
- **Development Guide**: See [CLAUDE.md](./CLAUDE.md) for development patterns and best practices
- **API Documentation**: Available at `/api/v1/docs` when backend is running

## Development

Each component has its own development workflow and requirements. Please refer to the individual README files in the `backend/` and `frontend/` directories for detailed instructions.

### Key Technologies

**Backend**: FastAPI, SQLAlchemy, PyJWT, pytest, ruff  
**Frontend**: Nuxt 3, Vue 3, shadcn-vue, Tailwind CSS, TypeScript

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the patterns in CLAUDE.md
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the GPL-3.0 License - see the LICENSE file for details.
