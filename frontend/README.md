# Prebetter Frontend

A modern Security Information and Event Management (SIEM) dashboard built with Nuxt 3, providing real-time visualization and management of security alerts from Prelude IDS/SIEM systems.

## Features

- **Real-time Security Dashboard**: Interactive visualization of security alerts and system status
- **Alert Management**: Filter, sort, and export security alerts with advanced filtering
- **System Health Monitoring**: Monitor heartbeat status of security agents across your network
- **Statistical Analysis**: Timeline charts and summary statistics for security events
- **Dark/Light Mode**: Built-in theme support with smooth transitions
- **Responsive Design**: Optimized for desktop and mobile devices

## Tech Stack

- **Framework**: Nuxt 3 with Vue 3 (Composition API)
- **UI Components**: shadcn-vue (Reka UI)
- **Styling**: Tailwind CSS v4 with CSS variables
- **Icons**: Lucide icons via @nuxt/icon
- **Package Manager**: Bun (required)
- **Type Checking**: TypeScript with vue-tsc
- **Utilities**: VueUse composition utilities

## Prerequisites

- Node.js 20+
- Bun package manager
- Backend API running at `http://localhost:8000`

## Installation

1. **Install dependencies:**
   ```bash
   bun install
   ```

2. **Configure environment (if needed):**
   - The frontend expects the backend API at `http://localhost:8000`
   - Adjust in `nuxt.config.ts` if your API runs on a different port

3. **Start development server:**
   ```bash
   bun run dev
   ```

   The application will be available at `http://localhost:3000`

## Development

### Available Scripts

```bash
# Development server
bun run dev          # Start on port 3000

# Type checking
bun run typecheck    # Run TypeScript type checking

# Building
bun run build        # Build for production
bun run preview      # Preview production build
bun run generate     # Generate static site

# Testing
bun run test         # Run tests with Vitest

# UI Components
bunx shadcn-vue@latest add <component-name>  # Add new UI component
```

### Project Structure

```
frontend/
├── app/
│   ├── assets/css/       # Global styles and Tailwind CSS
│   ├── components/       # Vue components
│   │   ├── ui/          # shadcn-vue UI components
│   │   ├── Navbar.vue   # Main navigation
│   │   └── ...          # Feature components
│   ├── composables/      # Reusable composition functions
│   ├── layouts/          # Page layouts
│   ├── pages/            # File-based routing
│   └── utils/            # Utility functions
├── server/               # Server-side code (BFF if needed)
├── public/               # Static assets
├── nuxt.config.ts        # Nuxt configuration
├── package.json          # Dependencies
├── components.json       # shadcn-vue configuration
└── tsconfig.json         # TypeScript configuration
```

### Key Components

- **Alert Dashboard**: Main dashboard displaying security alerts
- **Data Tables**: Sortable, filterable tables with pagination
- **Chart Components**: Timeline visualizations for security events
- **Filter System**: Advanced filtering for alerts by severity, classification, IP, etc.
- **Authentication**: JWT-based auth integration with backend

## API Integration

The frontend connects to the Prebetter backend API:

- **Base URL**: `http://localhost:8000/api/v1`
- **Authentication**: JWT Bearer tokens
- **Key Endpoints**:
  - `/alerts/` - Security alerts
  - `/statistics/` - Dashboard statistics
  - `/heartbeats/` - Agent status
  - `/reference/` - Classifications and severities

## Styling Guidelines

- Use Tailwind CSS classes inline
- Use predefined color variables (e.g., `bg-background`, `text-foreground`)
- Dark/light mode is handled automatically
- Icons use Lucide via `<Icon name="lucide:icon-name" />`

## Building for Production

```bash
# Build the application
bun run build

# Preview the production build
bun run preview

# Generate static site (if applicable)
bun run generate
```

## Contributing

1. Follow the existing code patterns and conventions
2. Use Composition API with TypeScript
3. Add appropriate type definitions
4. Test your changes thoroughly
5. Ensure linting passes

## License

Part of the Prebetter SIEM Dashboard project - see root LICENSE file for details.