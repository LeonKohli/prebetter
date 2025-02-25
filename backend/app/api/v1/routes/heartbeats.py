from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, case, literal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from collections import defaultdict
from pydantic import BaseModel, Field

from ....database.config import get_prelude_db
from ....database.query_builders import (
    build_heartbeats_timeline_query,
    build_efficient_heartbeats_query
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
    - model: The model of the analyzer
    - version: The version of the analyzer
    - class: The class of the analyzer
    - last_heartbeat: The timestamp of the last heartbeat
    - seconds_ago: Seconds since the last heartbeat
    - status: Current status (online/offline)
    
    When group_by_host=True, results are grouped by host with nested analyzers.
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
