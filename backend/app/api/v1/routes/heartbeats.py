from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from collections import defaultdict
from typing import Annotated, Dict, Any
from pydantic import ValidationError
import logging

from app.database.config import get_prelude_db
from app.database.query_builders import (
    build_heartbeats_timeline_query,
    build_efficient_heartbeats_query,
)
from app.database.cleanup import cleanup_old_heartbeats, cleanup_orphaned_analyzer_times
from app.core.datetime_utils import get_time_range
from app.models.prelude import AnalyzerTime
from app.models.users import User
from app.schemas.prelude import (
    HeartbeatTreeResponse,
    HeartbeatNodeInfo,
    AgentInfo,
    HeartbeatTimelineItem,
    PaginatedHeartbeatTimelineResponse,
)
from app.api.v1.routes.auth import get_current_user
from app.api.v1.routes.users import get_current_superuser

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


@router.get("/status", response_model=HeartbeatTreeResponse)
async def heartbeat_status(
    days: int = Query(1, ge=1, le=30, description="Days of history to look back"),
    db: Session = Depends(get_prelude_db),
):
    query = build_efficient_heartbeats_query(db, days)
    results = query.all()

    nodes_dict: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"name": "", "os": None, "agents": {}}
    )
    total_agents = 0

    for row in results:
        node_name = row.host_name or "(no node)"

        if not nodes_dict[node_name]["os"] and hasattr(row, "os"):
            nodes_dict[node_name]["os"] = row.os.strip() if row.os else None

        nodes_dict[node_name]["name"] = node_name

        if row.analyzer_name not in nodes_dict[node_name]["agents"]:
            try:
                last_heartbeat = (
                    None if row.last_heartbeat == "Never" else row.last_heartbeat
                )

                agent_info = AgentInfo(
                    name=row.analyzer_name,
                    model=row.model,
                    version=row.version,
                    **{
                        "class": getattr(row, "class")
                    },
                    latest_heartbeat_at=last_heartbeat,
                    seconds_ago=row.seconds_ago if row.seconds_ago is not None else -1,
                    status=row.status,
                )
                nodes_dict[node_name]["agents"][row.analyzer_name] = agent_info
            except ValidationError as e:
                logger.warning(f"Validation error for agent {row.analyzer_name}: {e}")
                continue

            total_agents += 1

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

    return HeartbeatTreeResponse(
        nodes=formatted_nodes,
        total_nodes=len(formatted_nodes),
        total_agents=total_agents,
    )


@router.get("/timeline", response_model=PaginatedHeartbeatTimelineResponse)
async def timeline_heartbeats(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to show"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_prelude_db),
):
    start_time, _ = get_time_range(hours)

    timeline_query = build_heartbeats_timeline_query(db, start_time)

    total_count = timeline_query.count()

    results = (
        timeline_query.order_by(AnalyzerTime.time.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    timeline_items = []
    for result in results:
        item = {
            "timestamp": result.timestamp,
            "host_name": result.host_name or "Unknown host",
            "analyzer_name": result.analyzer_name or "Unknown analyzer",
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
            "pages": (total_count + size - 1) // size,
        },
    }


@router.post("/cleanup")
async def cleanup_heartbeats(
    _: Annotated[
        User, Depends(get_current_superuser)
    ],
    db: Session = Depends(get_prelude_db),
    retention_days: int = Query(
        30, ge=1, le=90, description="Days of heartbeat data to retain"
    ),
    dry_run: bool = Query(
        False,
        description="If true, only preview what would be deleted without actually deleting",
    ),
):
    from app.models.prelude import Heartbeat

    total_heartbeats_before = db.query(Heartbeat).count()

    deleted_heartbeats, deleted_analyzer_times = cleanup_old_heartbeats(
        db, retention_days, dry_run=dry_run
    )

    deleted_orphans = cleanup_orphaned_analyzer_times(db, dry_run=dry_run)

    total_heartbeats_after = db.query(Heartbeat).count()

    return {
        "deleted_heartbeats": deleted_heartbeats,
        "deleted_analyzer_times": deleted_analyzer_times,
        "deleted_orphaned_records": deleted_orphans,
        "retention_days": retention_days,
        "dry_run": dry_run,
        "total_heartbeats_before": total_heartbeats_before,
        "total_heartbeats_after": total_heartbeats_after,
    }
