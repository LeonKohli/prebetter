from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .core.config import get_settings
from .core.logging import setup_logging, log_request
from .api.base import api_router
import time

# Set up logging
setup_logging()

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Prelude API",
    description="API for accessing Prelude data",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all requests with timing information"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    log_request(request, response.status_code, duration)
    return response

# Include API router with v1 prefix
app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["status"])
async def root():
    """
    Root endpoint providing API status and documentation links.
    
    Returns:
        dict: API status information and documentation URLs
    """
    return {
        "status": "online",
        "message": "Welcome to Prelude SIEM API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }
