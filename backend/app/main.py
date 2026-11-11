import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opensearchpy.exceptions import ConnectionError as OpenSearchConnectionError

from .api.base import api_router
from .api.deps import Alerts
from .core.config import get_settings
from .core.logging import setup_logging
from .middleware.setup import setup_middleware
from .opensearch.client import create_client
from .services.health import HealthResponse, get_health_status

settings = get_settings()
setup_logging(log_level=settings.LOG_LEVEL, environment=settings.ENVIRONMENT)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.opensearch = create_client(settings)
    try:
        yield
    finally:
        await app.state.opensearch.close()


description = """
Read-only API for the IDS alerts stored in OpenSearch.

* **Alerts**: filtered and sorted list, groups per address pair, detail, change stream
* **Statistics**: alert timeline
* **Reference**: severities, sensors and classifications for the filters
* **Health**: monitoring endpoint

Requests are authenticated with a Better Auth JWT.
"""

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=description,
    summary="IDS alert API on OpenSearch",
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


@app.exception_handler(OpenSearchConnectionError)
async def opensearch_unreachable(request: Request, exc: OpenSearchConnectionError):
    logger.error("OpenSearch unreachable: %s", exc)
    return JSONResponse(
        status_code=503, content={"detail": "OpenSearch is unavailable"}
    )


@app.get("/", tags=["status"])
async def root(request: Request) -> dict[str, str]:
    """API status and documentation links."""
    return {
        "status": "online",
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs_url": str(request.url_for("swagger_ui_html")),
        "redoc_url": str(request.url_for("redoc_html")),
    }


@app.get("/health", tags=["health"])
async def health_check(repo: Alerts) -> HealthResponse:
    """Liveness and OpenSearch reachability for load balancers and monitoring."""
    return await get_health_status(repo)
