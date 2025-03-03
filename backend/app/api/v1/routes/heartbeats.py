from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Union
from collections import defaultdict
from pydantic import BaseModel, Field

from ....database.config import get_prelude_db
from ....database.query_builders import (
    build_heartbeats_timeline_query,
    build_efficient_heartbeats_query
)
from ....core.datetime_utils import get_time_range
from ....models.prelude import AnalyzerTime
from ....schemas.prelude import (
    HeartbeatTreeResponse,
    HeartbeatNodeInfo,
    HeartbeatTimelineItem,
    PaginatedHeartbeatTimelineResponse,
)
from ..routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

# Define a model for the flat heartbeat status response
class HeartbeatStatusItem(BaseModel):
    host_name: str
    analyzer_name: str
    model: str
    version: str
    class_: str = Field(..., alias="class")
    last_heartbeat: str
    seconds_ago: int
    status: str

@router.get("/status", response_model=Union[List[HeartbeatStatusItem], HeartbeatTreeResponse])
async def heartbeat_status(
    days: int = Query(1, ge=1, le=30, description="Days of history to look back"),
    group_by_host: bool = Query(False, description="Group results by host"),
    db: Session = Depends(get_prelude_db),
):
    """
    Returns a list of all analyzers with their current status (online/offline).
    
    This endpoint uses an optimized query that:
    1. Gets the latest heartbeats within the specified time period
    2. Joins with analyzer and node information
    3. Calculates the online/offline status based on heartbeat time
    
    The response includes:
    - host_name: The name of the host
    - analyzer_name: The name of the analyzer
    - model: The analyzer model
    - version: The analyzer version
    - class: Classification of the analyzer
    - last_heartbeat: Timestamp of the most recent heartbeat
    - seconds_ago: Seconds since the last heartbeat
    - status: "online" or "offline" based on a threshold
    """
    # Use the efficient query builder
    query = build_efficient_heartbeats_query(db, days)
    results = query.all()
    
    if not group_by_host:
        # Return flat list format matching the SQL query output
        output = []
        for row in results:
            # Ensure field order matches the SQL query output
            output.append({
                "host_name": row.host_name,
                "analyzer_name": row.analyzer_name,
                "model": row.model,
                "version": row.version,
                "class": row.class_,
                "last_heartbeat": row.last_heartbeat,
                "seconds_ago": row.seconds_ago,
                "status": row.status
            })
        return output
    else:
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
                nodes_dict[node_name]["agents"][row.analyzer_name] = {
                    "name": row.analyzer_name,
                    "model": row.model,
                    "version": row.version,
                    "class": row.class_,
                    "latest_heartbeat": row.last_heartbeat,  # Match field name in AgentInfo schema
                    "seconds_ago": row.seconds_ago,
                    "status": row.status,
                }
                total_agents += 1

        # Convert to list and create response
        formatted_nodes = []
        for node_name, node_data in nodes_dict.items():
            # Convert the agents dictionary to a list
            agents_list = list(node_data["agents"].values())
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
    page_size: int = Query(100, ge=1, le=1000),
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
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    # Convert results to response model
    timeline_items = [
        HeartbeatTimelineItem(
            time=result.time.isoformat(),
            host_name=result.host_name,
            analyzer_name=result.analyzer_name,
            model=result.model,
            version=result.version,
            class_=result.class_,
        )
        for result in results
    ]
    
    # Return with pagination metadata
    return {
        "items": timeline_items,
        "pagination": {
            "total": total_count,
            "page": page,
            "size": page_size,
            "pages": (total_count + page_size - 1) // page_size
        }
    }
