from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import time
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_HEALTH_STATE = {
    "api_start_time": time.time(),
    "prelude_db_available": False,
    "prebetter_db_available": False,
    "ready": False,
}


class HealthResponse(BaseModel):
    status: str = Field(
        ..., description="Overall system status: healthy, degraded, or unhealthy"
    )
    prelude_db: bool = Field(
        ..., description="Prelude database connection availability"
    )
    prebetter_db: bool = Field(
        ..., description="Prebetter database connection availability"
    )
    uptime_seconds: float = Field(..., description="API uptime in seconds")
    timestamp: str = Field(..., description="Current server timestamp")


def update_health_state(
    prelude_available: Optional[bool] = None,
    prebetter_available: Optional[bool] = None,
    ready: Optional[bool] = None,
) -> None:
    global _HEALTH_STATE

    if prelude_available is not None:
        _HEALTH_STATE["prelude_db_available"] = prelude_available

    if prebetter_available is not None:
        _HEALTH_STATE["prebetter_db_available"] = prebetter_available

    if ready is not None:
        _HEALTH_STATE["ready"] = ready


def get_health_status() -> HealthResponse:
    status = "healthy"

    if not _HEALTH_STATE["prelude_db_available"]:
        status = "unhealthy"
    elif not _HEALTH_STATE["prebetter_db_available"]:
        status = "degraded"

    if not _HEALTH_STATE["ready"]:
        status = "starting"

    uptime = time.time() - _HEALTH_STATE["api_start_time"]

    return HealthResponse(
        status=status,
        prelude_db=_HEALTH_STATE["prelude_db_available"],
        prebetter_db=_HEALTH_STATE["prebetter_db_available"],
        uptime_seconds=uptime,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def check_database_health(db: Session, db_type: str) -> Dict[str, Any]:
    try:
        db.execute(text("SELECT 1")).scalar()

        if db_type == "prelude":
            update_health_state(prelude_available=True)
        elif db_type == "prebetter":
            update_health_state(prebetter_available=True)

        return {"connected": True}
    except Exception as e:
        logger.error(f"Database connection check failed for {db_type}: {e}")

        if db_type == "prelude":
            update_health_state(prelude_available=False)
        elif db_type == "prebetter":
            update_health_state(prebetter_available=False)

        return {"connected": False, "error": str(e)}
