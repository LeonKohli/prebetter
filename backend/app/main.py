from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import get_settings
from .core.logging import setup_logging
from .api.base import api_router
from .database.init_db import ensure_database
import logging
from contextlib import asynccontextmanager

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    logger.info("Initializing database...")
    await ensure_database()
    logger.info("Database initialization complete.")
    yield

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for accessing Prelude data and managing users",
    version=settings.VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }
