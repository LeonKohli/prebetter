from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
import time
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Global health state
_HEALTH_STATE = {
    "api_start_time": time.time(),
    "prelude_db_available": False,
    "prebetter_db_available": False,
    "ready": False
}

class HealthResponse(BaseModel):
    """Health status response model."""
    status: str = Field(..., description="Overall system status: healthy, degraded, or unhealthy")
    prelude_db: bool = Field(..., description="Prelude database connection availability")
    prebetter_db: bool = Field(..., description="Prebetter database connection availability")
    uptime_seconds: float = Field(..., description="API uptime in seconds")
    timestamp: str = Field(..., description="Current server timestamp")


def update_health_state(prelude_available: bool = None, prebetter_available: bool = None, ready: bool = None) -> None:
    """
    Update the internal health state.
    
    Args:
        prelude_available: Prelude database availability
        prebetter_available: Prebetter database availability
        ready: Application readiness status
    """
    global _HEALTH_STATE
    
    if prelude_available is not None:
        _HEALTH_STATE["prelude_db_available"] = prelude_available
    
    if prebetter_available is not None:
        _HEALTH_STATE["prebetter_db_available"] = prebetter_available
    
    if ready is not None:
        _HEALTH_STATE["ready"] = ready


def get_health_status() -> Dict[str, Any]:
    """
    Get health status of the API.
    
    This function returns the basic health status, including:
    - Overall status ("healthy", "degraded", "unhealthy")
    - Database availability 
    - API uptime and server timestamp
    
    Available at:
    - /health (root endpoint)
    
    Returns:
        Dictionary with health status information
    """
    # Determine overall status
    status = "healthy"
    
    # If Prelude DB is unavailable, we're "unhealthy"
    if not _HEALTH_STATE["prelude_db_available"]:
        status = "unhealthy"
    # If only Prebetter DB is unavailable, we're "degraded"
    elif not _HEALTH_STATE["prebetter_db_available"]:
        status = "degraded"
    
    # If not yet ready, show "starting"
    if not _HEALTH_STATE["ready"]:
        status = "starting"
    
    # Calculate uptime
    uptime = time.time() - _HEALTH_STATE["api_start_time"]
    
    return {
        "status": status,
        "prelude_db": _HEALTH_STATE["prelude_db_available"],
        "prebetter_db": _HEALTH_STATE["prebetter_db_available"],
        "uptime_seconds": uptime,
        "timestamp": datetime.now().isoformat()
    }


def check_database_health(db: Session, db_type: str) -> Dict[str, Any]:
    """
    Check the health of a database connection.
    
    This function is used during application startup and
    periodic health checks to update the global health state.
    
    Args:
        db: SQLAlchemy database session
        db_type: Type of database ('prelude' or 'prebetter')
        
    Returns:
        Dictionary with connection status information
    """
    try:
        # Simple query to test connection
        db.execute(text("SELECT 1")).scalar()
        
        # Update global health state
        if db_type == "prelude":
            update_health_state(prelude_available=True)
        elif db_type == "prebetter":
            update_health_state(prebetter_available=True)
        
        return {
            "connected": True
        }
    except Exception as e:
        logger.error(f"Database connection check failed for {db_type}: {str(e)}")
        
        # Update global health state
        if db_type == "prelude":
            update_health_state(prelude_available=False)
        elif db_type == "prebetter":
            update_health_state(prebetter_available=False)
        
        return {
            "connected": False,
            "error": str(e)
        }