import time
from datetime import datetime, UTC

from opensearchpy.exceptions import TransportError
from pydantic import BaseModel

from app.repositories.alerts import AlertRepository

_STARTED_AT = time.monotonic()


class HealthResponse(BaseModel):
    status: str
    opensearch: bool
    uptime_seconds: float
    timestamp: str


async def get_health_status(repo: AlertRepository) -> HealthResponse:
    """`healthy` when a count on the index pattern succeeds (index-level read is all it needs)."""
    try:
        await repo.count(timeout=2)
        reachable = True
    except TransportError:
        reachable = False
    return HealthResponse(
        status="healthy" if reachable else "unhealthy",
        opensearch=reachable,
        uptime_seconds=time.monotonic() - _STARTED_AT,
        timestamp=datetime.now(UTC).isoformat(),
    )
