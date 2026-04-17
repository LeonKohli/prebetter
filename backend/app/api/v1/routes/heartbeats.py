import asyncio
import logging
from collections import Counter, defaultdict
from datetime import datetime
from collections.abc import AsyncIterable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.datetime_utils import ensure_timezone, get_current_time, get_time_range
from app.database.config import PreludeSessionLocal, get_prelude_db
from app.database.models import determine_heartbeat_status
from app.database.query_builders import (
    build_efficient_heartbeats_query,
    build_heartbeats_timeline_query,
)
from app.models.prelude import AnalyzerTime
from app.schemas.filters import calculate_total_pages
from app.schemas.prelude import (
    AgentInfo,
    HeartbeatNodeInfo,
    HeartbeatTimelineItem,
    HeartbeatTreeResponse,
    PaginatedHeartbeatTimelineResponse,
)

router = APIRouter(dependencies=[Depends(get_current_user, scope="function")])
logger = logging.getLogger(__name__)


HEARTBEAT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_last_heartbeat(raw_value: Any) -> datetime | None:
    """Return a timezone-aware datetime for a raw heartbeat column."""
    if raw_value in (None, "Never"):
        return None

    parsed_value = raw_value
    if isinstance(raw_value, str):
        try:
            parsed_value = datetime.strptime(raw_value, HEARTBEAT_TIME_FORMAT)
        except ValueError:
            return None

    return ensure_timezone(parsed_value)


def _normalise_interval(raw_interval: Any) -> int | None:
    """Convert persisted heartbeat intervals to a positive integer or None."""
    if raw_interval is None:
        return None
    try:
        interval = int(raw_interval)
    except (TypeError, ValueError):
        return None
    return interval if interval > 0 else None


def _derive_heartbeat_metadata(
    row: dict[str, Any], now: datetime
) -> tuple[datetime | None, int, str, int | None]:
    """Compute heartbeat metadata for response payloads."""
    last_heartbeat = _parse_last_heartbeat(getattr(row, "last_heartbeat", None))
    interval = _normalise_interval(getattr(row, "heartbeat_interval", None))

    seconds_ago = -1
    seconds_diff: int | None = None
    if last_heartbeat is not None:
        seconds_diff = int((now - last_heartbeat).total_seconds())
        seconds_ago = max(seconds_diff, 0)

    if interval is None:
        # Without an interval we cannot classify activity reliably.
        return last_heartbeat, seconds_ago, "unknown", None

    status = determine_heartbeat_status(last_heartbeat, now, interval)

    return last_heartbeat, seconds_ago, status, interval


# SSE endpoint for real-time heartbeat updates
# IMPORTANT: Must be defined BEFORE any path-parameter routes
@router.get("/stream", response_class=EventSourceResponse)
async def stream_heartbeats(
    request: Request,
    last_timestamp: Annotated[
        str | None,
        Query(description="Last known heartbeat timestamp (ISO format)"),
    ] = None,
) -> AsyncIterable[ServerSentEvent]:
    """
    Server-Sent Events endpoint for real-time heartbeat updates.

    Connect with EventSource and receive notifications when new heartbeats arrive.
    Pass `last_timestamp` (ISO format) to only receive updates for newer heartbeats.

    IMPORTANT: This endpoint does NOT hold a database connection for the stream lifetime.
    Each poll acquires and releases a fresh session to avoid exhausting the pool.
    """

    # Parse initial timestamp if provided
    current_last_ts: datetime | None = None
    if last_timestamp:
        try:
            current_last_ts = datetime.fromisoformat(
                last_timestamp.replace("Z", "+00:00")
            )
            current_last_ts = ensure_timezone(current_last_ts)
        except ValueError:
            pass  # Invalid format, start fresh

    # If no timestamp provided, get current max to avoid sending all historical data
    if current_last_ts is None:
        with PreludeSessionLocal() as db:
            max_ts = db.scalar(
                select(func.max(AnalyzerTime.time)).where(
                    AnalyzerTime._parent_type == "H"
                )
            )
            if max_ts:
                current_last_ts = ensure_timezone(max_ts)

    # Send immediate comment to establish connection
    # This transitions EventSource from CONNECTING to OPEN instantly
    yield ServerSentEvent(comment="connected")

    while True:
        if await request.is_disconnected():
            break

        # Acquire fresh session for EACH poll - releases immediately after
        # This is critical: SSE connections can live for hours/days
        with PreludeSessionLocal() as db:
            query = select(
                func.max(AnalyzerTime.time).label("latest_ts"),
                func.count(AnalyzerTime.time).label("new_count"),
            ).where(AnalyzerTime._parent_type == "H")

            if current_last_ts:
                query = query.where(AnalyzerTime.time > current_last_ts)

            result = db.execute(query).first()

            if result and result.latest_ts and result.new_count > 0:
                latest_ts = ensure_timezone(result.latest_ts)

                yield ServerSentEvent(
                    data={
                        "latest_timestamp": latest_ts.isoformat(),
                        "new_count": result.new_count,
                    },
                    event="heartbeat_update",
                )

                current_last_ts = latest_ts

        # Session is now CLOSED - connection returned to pool
        await asyncio.sleep(5)


@router.get("/status", response_model=HeartbeatTreeResponse)
def heartbeat_status(
    db: Annotated[Session, Depends(get_prelude_db)],
    days: Annotated[
        int, Query(ge=1, le=30, description="Days of history to look back")
    ] = 1,
):
    query = build_efficient_heartbeats_query(db, days)
    results = db.execute(query).all()

    nodes_dict: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"name": "", "os": None, "agents": {}}
    )
    total_agents = 0
    status_counts: Counter[str] = Counter()
    now = get_current_time()

    for row in results:
        node_name = row.host_name or "(no node)"

        if not nodes_dict[node_name]["os"] and hasattr(row, "os"):
            nodes_dict[node_name]["os"] = row.os.strip() if row.os else None

        nodes_dict[node_name]["name"] = node_name

        if row.analyzer_name not in nodes_dict[node_name]["agents"]:
            try:
                (
                    last_heartbeat,
                    seconds_ago,
                    status,
                    heartbeat_interval,
                ) = _derive_heartbeat_metadata(row, now)

                agent_info = AgentInfo(
                    name=row.analyzer_name,
                    model=row.model,
                    version=row.version,
                    **{"class": getattr(row, "class")},
                    latest_heartbeat_at=last_heartbeat,
                    seconds_ago=seconds_ago,
                    heartbeat_interval=heartbeat_interval,
                    status=status,
                )
                nodes_dict[node_name]["agents"][row.analyzer_name] = agent_info
            except ValidationError as e:
                logger.warning(f"Validation error for agent {row.analyzer_name}: {e}")
                continue

            total_agents += 1
            status_counts[status] += 1

    formatted_nodes = []
    for node_name, node_data in nodes_dict.items():
        agents_list = [
            agent for agent in node_data["agents"].values() if agent is not None
        ]
        formatted_nodes.append(
            HeartbeatNodeInfo(
                name=node_name, os=node_data.get("os"), agents=agents_list
            )
        )

    summary = {
        status: status_counts.get(status, 0)
        for status in ("active", "inactive", "offline", "unknown")
    }
    for extra_status, count in status_counts.items():
        if extra_status not in summary:
            summary[extra_status] = count

    return HeartbeatTreeResponse(
        nodes=formatted_nodes,
        total_nodes=len(formatted_nodes),
        total_agents=total_agents,
        status_summary=summary,
    )


@router.get("/timeline", response_model=PaginatedHeartbeatTimelineResponse)
def timeline_heartbeats(
    db: Annotated[Session, Depends(get_prelude_db)],
    hours: Annotated[
        int, Query(ge=1, le=168, description="Hours of history to show")
    ] = 24,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=1000)] = 100,
):
    """Heartbeat timeline with larger page size (up to 1000) for history views."""
    start_time, _ = get_time_range(hours)

    timeline_query = build_heartbeats_timeline_query(db, start_time)

    count_subquery = timeline_query.subquery()
    total_count = db.scalar(select(func.count()).select_from(count_subquery)) or 0

    results = db.execute(
        timeline_query.order_by(AnalyzerTime.time.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    timeline_items = []
    for result in results:
        host_name = result.host_name or "(no node)"
        analyzer_name = result.analyzer_name or "Unknown analyzer"

        item = {
            "timestamp": ensure_timezone(result.timestamp),
            "host_name": host_name,
            "analyzer_name": analyzer_name,
            "model": result.model or "",
            "version": result.version or "",
            "class_": result.class_ or "",
        }
        timeline_items.append(HeartbeatTimelineItem(**item))

    return {
        "items": timeline_items,
        "pagination": {
            "total": total_count,
            "page": page,
            "size": size,
            "pages": calculate_total_pages(total_count, size),
        },
    }
