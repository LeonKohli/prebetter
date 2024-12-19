from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.endpoints import router as api_router

app = FastAPI(
    title="Prelude SIEM API",
    description="""
    A comprehensive read-only API for accessing and analyzing Prelude IDS/SIEM data.
    
    Key Features:
    - **Alert Management**
      * Comprehensive alert information with timing, classification, and severity
      * Source and target address details with complete network information
      * Detailed analyzer information including node and process details
      * Full payload access with optional truncation
    
    - **Advanced Filtering**
      * Date range filtering with timezone support
      * Multiple filter criteria (severity, classification, IPs, analyzer)
      * Flexible sorting options
      * Configurable pagination
    
    - **Analysis Tools**
      * Statistical summaries of alert data
      * Timeline visualization with customizable time frames
      * Top threats and sources analysis
      * Severity distribution insights
    
    - **Performance Optimizations**
      * Efficient database queries
      * Connection pooling
      * Optional payload truncation
      * Response caching support
    
    All endpoints are documented with detailed request/response schemas and examples.
    Use the interactive documentation below to explore the API capabilities.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router
app.include_router(
    api_router,
    prefix="/api",
    tags=["alerts"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"},
    },
)


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
