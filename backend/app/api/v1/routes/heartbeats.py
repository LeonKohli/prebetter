from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from collections import defaultdict
from typing import Annotated
from datetime import datetime

from app.database.config import get_prelude_db
from app.database.query_builders import (
    build_heartbeats_timeline_query,
    build_efficient_heartbeats_query
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

@router.get("/status", response_model=HeartbeatTreeResponse)
async def heartbeat_status(
    days: int = Query(1, ge=1, le=30, description="Days of history to look back"),
    db: Session = Depends(get_prelude_db),
):
    """
    Returns a tree structure of all analyzers grouped by host with their current status (online/offline).
    
    This endpoint uses an optimized query that:
    1. Gets the latest heartbeats within the specified time period
    2. Joins with analyzer and node information
    3. Calculates the online/offline status based on heartbeat time
    4. Groups results by host in a hierarchical structure
    
    The response includes:
    - A list of nodes (hosts), each containing:
      - name: The name of the host
      - os: Operating system of the host
      - agents: List of analyzers running on the host, each containing:
        - name: The name of the analyzer
        - model: The analyzer model
        - version: The analyzer version
        - class: Classification of the analyzer
        - latest_heartbeat: Timestamp of the most recent heartbeat
        - seconds_ago: Seconds since the last heartbeat
        - status: "online" or "offline" based on a threshold
    - total_nodes: Total number of hosts
    - total_agents: Total number of unique analyzers
    """
    # Use the efficient query builder
    query = build_efficient_heartbeats_query(db, days)
    results = query.all()
    
    # Group by node for tree structure
    nodes_dict = defaultdict(lambda: {"name": "", "os": None, "agents": {}})
    total_agents = 0

    for row in results:
        node_name = row.host_name or "(no node)"
        
        # Add agent to the node if it doesn't already exist
        if not nodes_dict[node_name]["os"] and row.os:
            nodes_dict[node_name]["os"] = row.os
            
        nodes_dict[node_name]["name"] = node_name
        
        # Use a dictionary to track unique agents by name
        if row.analyzer_name not in nodes_dict[node_name]["agents"]:
            # Handle potential non-datetime last_heartbeat
            last_hb = row.last_heartbeat
            if not isinstance(last_hb, datetime):
                last_hb = None # Or parse if possible, or log warning
                
            # Create AgentInfo object matching the schema
            agent_info_data = {
                "name": row.analyzer_name,
                "model": row.model,
                "version": row.version,
                "class_": row.class_, # Use field name with underscore
                "latest_heartbeat_at": last_hb,  # Use potentially corrected value
                "seconds_ago": row.seconds_ago,
                "status": row.status,
            }
            try:
                nodes_dict[node_name]["agents"][row.analyzer_name] = AgentInfo(**agent_info_data)
            except Exception as e:
                # Log the error and skip this agent, or handle more gracefully
                print(f"Error creating AgentInfo for {row.analyzer_name}: {e}") 
                # Optionally: nodes_dict[node_name]["agents"][row.analyzer_name] = None # Or a placeholder
                continue # Skip adding this agent if validation fails

            total_agents += 1

    # Convert to list and create tree response
    formatted_nodes = []
    for node_name, node_data in nodes_dict.items():
        # Filter out potential None values if validation failed
        agents_list = [agent for agent in node_data["agents"].values() if agent is not None]
        formatted_nodes.append(HeartbeatNodeInfo(
            name=node_data["name"],
            os=node_data["os"],
            agents=agents_list
        ))
    
    return HeartbeatTreeResponse(
        nodes=formatted_nodes,
        total_nodes=len(formatted_nodes),
        total_agents=total_agents
    )


@router.get("/timeline", response_model=PaginatedHeartbeatTimelineResponse)
async def timeline_heartbeats(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to show"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_prelude_db),
):
    """
    Returns a timeline of heartbeats from analyzers.
    Useful for monitoring the health of analyzers over time.
    """
    # Calculate time range using utility function
    start_time, end_time = get_time_range(hours)

    # Use query builder to get the timeline query
    timeline_query = build_heartbeats_timeline_query(db, start_time)
    
    # Get total count for pagination info
    total_count = timeline_query.count()

    # Apply pagination and ordering
    results = (
        timeline_query.order_by(AnalyzerTime.time.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    
    # Convert results to response model
    timeline_items = []
    for result in results:
        # Create item with proper field mapping
        item = {
            "timestamp": result.timestamp, # Updated field name, assuming result.timestamp is datetime
            "host_name": result.host_name or "Unknown host",
            "analyzer_name": result.analyzer_name or "Unknown analyzer",
            "model": result.model or "",
            "version": result.version or "",
            "class_": result.class_ or "", # Use alias for class_
        }
        timeline_items.append(HeartbeatTimelineItem(**item))
    
    # Return with pagination metadata
    return {
        "items": timeline_items,
        "pagination": {
            "total": total_count,
            "page": page,
            "size": size,
            "pages": (total_count + size - 1) // size
        }
    }

@router.post("/cleanup")
async def cleanup_heartbeats(
    current_user: Annotated[User, Depends(get_current_superuser)],  # Use superuser check
    db: Session = Depends(get_prelude_db),
    retention_days: int = Query(30, ge=7, le=90, description="Days of heartbeat data to retain"),
):
    """
    Clean up old heartbeat data and orphaned records.
    This is an administrative endpoint that requires superuser privileges.
    
    Args:
        current_user: Current superuser (injected by dependency)
        db: Database session
        retention_days: Number of days of heartbeat data to retain (7-90 days)
        
    Returns:
        Dict with cleanup statistics
    """
    # Clean up old heartbeats first
    deleted_heartbeats, deleted_analyzer_times = cleanup_old_heartbeats(db, retention_days)
    
    # Then clean up any orphaned analyzer times
    deleted_orphans = cleanup_orphaned_analyzer_times(db)
    
    return {
        "deleted_heartbeats": deleted_heartbeats,
        "deleted_analyzer_times": deleted_analyzer_times,
        "deleted_orphaned_records": deleted_orphans,
        "retention_days": retention_days
    }
