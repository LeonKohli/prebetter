from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, case, literal
from datetime import datetime, timedelta
from typing import List
from collections import defaultdict

from ....database.config import get_prelude_db
from ....database.query_builders import (
    build_heartbeats_tree_query,
    build_heartbeats_timeline_query
)
from ....database.models import (
    format_relative_time,
    determine_heartbeat_status
)
from ....models.prelude import Heartbeat, Analyzer, AnalyzerTime, Node, Address
from ....schemas.prelude import (
    HeartbeatTreeResponse,
    HeartbeatNodeInfo,
    AgentInfo,
    HeartbeatTimelineItem,
)
from ..routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/tree", response_model=HeartbeatTreeResponse)
async def tree_heartbeats(db: Session = Depends(get_prelude_db)):
    """
    Returns a list of nodes with their agents and total counts.
    """
    # Current time for calculating relative times and status
    current_time = datetime.utcnow()

    # Use query builder to get the tree query
    tree_query = build_heartbeats_tree_query(db)
    rows = tree_query.all()
    
    # Group by node
    nodes_dict = defaultdict(lambda: {"name": "", "os": None, "agents": []})
    total_agents = 0

    for row in rows:
        # Use utility functions to format relative time and determine status
        rel_time = format_relative_time(row.last_heartbeat, current_time)
        interval = row.heartbeat_interval or 600
        status = determine_heartbeat_status(row.last_heartbeat, current_time, interval)

        node_name = row.node_name or "(no node)"
        
        # Add agent to the node
        if not nodes_dict[node_name]["os"] and row.os:
            nodes_dict[node_name]["os"] = row.os
        nodes_dict[node_name]["name"] = node_name
        nodes_dict[node_name]["agents"].append({
            "name": row.name,
            "model": row.model,
            "version": row.version,
            "class": row.class_,
            "latest_heartbeat": rel_time,
            "status": status,
        })
        total_agents += 1

    # Convert to list and create response
    nodes = [HeartbeatNodeInfo(**node_data) for node_data in nodes_dict.values()]
    
    return HeartbeatTreeResponse(
        nodes=nodes,
        total_nodes=len(nodes),
        total_agents=total_agents
    )


@router.get("/timeline", response_model=List[HeartbeatTimelineItem])
async def timeline_heartbeats(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to show"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_prelude_db),
):
    """
    Returns a list of timeline heartbeat records, with optional pagination.
    [
      {
        "Date": "11 Feb 2025, 10:35:30",
        "Agent": "snort-eno5",
        "Node_Address": "10.129.9.52",
        "Node_Name": "beis-00072-012.lvnbb.de",
        "Model": "Snort"
      },
      ...
    ]
    """
    # Calculate cutoff time based on requested hours
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    # Use query builder to get the timeline query
    timeline_query = build_heartbeats_timeline_query(db, cutoff_time)
    
    # Get total count for pagination info
    total_count = timeline_query.count()

    # Apply pagination and ordering
    results = (
        timeline_query.order_by(AnalyzerTime.time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Format the results for the response
    output = []
    for row in results:
        formatted_date = row.timestamp.strftime("%d %b %Y, %H:%M:%S")
        output.append(
            {
                "Date": formatted_date,
                "Agent": row.agent,
                "Node_Address": row.node_address if row.node_address else row.node_name,
                "Node_Name": row.node_name,
                "Model": row.model,
            }
        )

    return output
