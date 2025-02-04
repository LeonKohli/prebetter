from fastapi import APIRouter
from .v1.routes import alerts_router, statistics_router, reference_router, auth_router

api_router = APIRouter()

# Include all v1 routes
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
api_router.include_router(statistics_router, prefix="/statistics", tags=["statistics"])
api_router.include_router(reference_router, tags=["reference"]) 