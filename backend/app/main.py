from fastapi import FastAPI
from .core.config import get_settings
from .core.logging import setup_logging
from .api.base import api_router
from .database.init_db import ensure_database, check_database_connections
from .services.health import update_health_state, get_health_status, HealthResponse
from .middleware.setup import setup_middleware
import logging
from contextlib import asynccontextmanager

# Get settings
settings = get_settings()

# Set up logging with settings from config
print(f"Initializing logging with level: {settings.LOG_LEVEL}, environment: {settings.ENVIRONMENT}")
setup_logging(log_level=settings.LOG_LEVEL, environment=settings.ENVIRONMENT)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    try:
        logger.info("Initializing prebetter database...")
        await ensure_database()
        update_health_state(prebetter_available=True)
        logger.info("Prebetter database initialization complete.")
        
        # Check Prelude database connection
        logger.info("Checking Prelude database connection...")
        prelude_ok = await check_database_connections(check_prelude=True, check_prebetter=False)
        update_health_state(prelude_available=prelude_ok)
        
        if prelude_ok:
            logger.info("Prelude database connection successful.")
        else:
            logger.warning("Prelude database connection failed. Some functionality will be limited.")
        
        # Set app as ready
        update_health_state(ready=True)
        logger.info("Application startup complete.")
        
        yield
    except Exception as e:
        logger.error(f"Error during application startup: {str(e)}")
        # We'll still mark the app as ready, but with limited functionality
        update_health_state(ready=True)
        yield
    finally:
        logger.info("Application shutdown.")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for accessing Prelude data",
    version=settings.VERSION,
    lifespan=lifespan,
    license_info={
        "name": "GPLv3",
        "url": "https://www.gnu.org/licenses/gpl-3.0.en.html",
    },
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

# Set up middleware
setup_middleware(app)

# Include API router with v1 prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["status"])
async def root():
    """
    Root endpoint providing API status and documentation links.
    
    Returns:
        dict: API status information and documentation URLs
    """
    return {
        "status": "online",
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs_url": f"http://localhost:8000{settings.API_V1_STR}/docs",
        "redoc_url": f"http://localhost:8000{settings.API_V1_STR}/redoc",
    }

# Health check endpoint for infrastructure monitoring
@app.get("/health", tags=["health"], response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for infrastructure monitoring.
    
    This endpoint is designed for:
    - Load balancers checking service availability
    - Monitoring systems tracking service health
    - Kubernetes liveness/readiness probes
    - Docker health checks
    
    It returns minimal but essential information about the service status.
    
    Returns:
        HealthResponse: Basic health status with database availability
    """
    return get_health_status()
