from fastapi import FastAPI, Request
from .core.config import get_settings
from .core.logging import setup_logging
from .api.base import api_router
from .database.init_db import (
    ensure_database,
    check_database_connections,
    check_pair_accelerator,
)
from .database.config import prelude_engine
from .repositories.alerts import reflect_pair_table
from .services.health import update_health_state, get_health_status, HealthResponse
from .middleware.setup import setup_middleware
import logging
from contextlib import asynccontextmanager

settings = get_settings()
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

        logger.info("Checking Prelude database connection...")
        prelude_ok = await check_database_connections(
            check_prelude=True, check_prebetter=False
        )
        update_health_state(prelude_available=prelude_ok)

        if prelude_ok:
            logger.info("Prelude database connection successful.")
        else:
            logger.warning(
                "Prelude database connection failed. Some functionality will be limited."
            )

        # Enforce presence of the pair-key accelerator; do not start without it
        try:
            check_pair_accelerator(strict=True)
        except Exception as e:
            logger.error(
                "Prebetter_Pair accelerator is required but not available: %s", str(e)
            )
            # Fail startup as requested: avoid unpredictable fallbacks
            raise

        # Reflect Prebetter_Pair table ONCE at startup, store in app.state
        # This avoids global mutable state and makes the table available via DI
        logger.info("Reflecting Prebetter_Pair table...")
        app.state.pair_table = reflect_pair_table(prelude_engine)
        if app.state.pair_table is not None:
            logger.info("Prebetter_Pair table reflected successfully.")
        else:
            logger.warning("Prebetter_Pair table not found - grouped alerts disabled.")

        update_health_state(ready=True)
        logger.info("Application startup complete.")

        yield
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        update_health_state(ready=False)
        raise
    finally:
        logger.info("Application shutdown.")


description = """
API for accessing and managing Prelude IDS data with comprehensive security alert management. 🚀

## Key Features

You can:
* **View and analyze alerts** with rich metadata
* **Authenticate users** with JWT and role-based access
* **Monitor heartbeats** from agents and analyzers
* **Generate statistics** and event timelines
* **Export data** in CSV format
* **Check health status** via monitoring endpoint

## Databases

We connect to:
* **Prelude DB** - For IDS data
* **Prebetter DB** - For auth and users

See the docs below for detailed API reference.
"""

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=description,
    summary="Comprehensive IDS data management API",
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

setup_middleware(app)
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["status"])
def root(request: Request) -> dict[str, str]:
    """
    Root endpoint providing API status and documentation links.

    Returns:
        dict: API status information and documentation URLs
    """
    docs_url = request.url_for("swagger_ui_html")
    redoc_url = request.url_for("redoc_html")

    return {
        "status": "online",
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs_url": str(docs_url),
        "redoc_url": str(redoc_url),
    }


@app.get("/health", tags=["health"], response_model=HealthResponse)
def health_check() -> HealthResponse:
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
