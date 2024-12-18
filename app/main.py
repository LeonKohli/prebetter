from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.endpoints import router as api_router

app = FastAPI(
    title="Prelude SIEM API",
    description="""
    Read-only API for accessing Prelude IDS/SIEM data.
    
    Key Features:
    - Comprehensive alert information including timing, classification, and severity
    - Source and target address details with node information
    - Analyzer details for each alert
    - Filtering capabilities by date, severity, classification, and IP addresses
    - Pagination support
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
    prefix="/api/v1",
    tags=["alerts"]
)

@app.get("/", tags=["status"])
async def root():
    return {
        "status": "online",
        "message": "Welcome to Prelude SIEM API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    } 