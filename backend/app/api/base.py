from fastapi import APIRouter
from .v1.routes import (
    alerts_router,
    statistics_router,
    reference_router,
    auth_router,
    users_router,
    export_router,
    heartbeats_router,
)

api_router = APIRouter()

# Include all v1 routes
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
api_router.include_router(statistics_router, prefix="/statistics", tags=["statistics"])
api_router.include_router(reference_router, prefix="/reference", tags=["reference"])
api_router.include_router(export_router, prefix="/export", tags=["export"])
api_router.include_router(heartbeats_router, prefix="/heartbeats", tags=["heartbeats"])
