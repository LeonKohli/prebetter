from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, case, literal
from datetime import datetime, timedelta
from typing import List
from collections import defaultdict

from ....database.config import get_prelude_db
from ....models.prelude import Heartbeat, Analyzer, AnalyzerTime, Node, Address
from ....schemas.prelude import (
    HeartbeatTreeResponse,
    HeartbeatNodeInfo,
    AgentInfo,
    HeartbeatTimelineItem,
)
from ..routes.auth import get_current_user

router = APIRouter()
# dependencies=[Depends(get_current_user)]

@router.get("/tree", response_model=HeartbeatTreeResponse)
async def tree_heartbeats(db: Session = Depends(get_prelude_db)):
    """
    Returns a list of nodes with their agents and total counts.
    """
    current_time = datetime.utcnow()

    # Single query: gather everything in one pass.
    q = (
        db.query(
            Analyzer.name.label("name"),
            Analyzer.model.label("model"),
            Analyzer.version.label("version"),
            getattr(Analyzer, "class").label("class_"),
            Node.name.label("node_name"),
            # Combine ostype and osversion for OS info
            case(
                (
                    Analyzer.ostype.isnot(None),
                    func.concat(
                        Analyzer.ostype,
                        literal(" "),
                        func.coalesce(Analyzer.osversion, "")
                    )
                ),
                else_=None
            ).label("os"),
            func.max(AnalyzerTime.time).label("last_heartbeat"),
            func.max(Heartbeat.heartbeat_interval).label("heartbeat_interval"),
        )
        .select_from(Analyzer)
        .outerjoin(
            Node,
            and_(
                Node._message_ident == Analyzer._message_ident,
                Node._parent_type == Analyzer._parent_type,
            ),
        )
        .outerjoin(
            Heartbeat,
            Heartbeat._ident == Analyzer._message_ident,
        )
        .outerjoin(
            AnalyzerTime,
            and_(
                AnalyzerTime._message_ident == Analyzer._message_ident,
                AnalyzerTime._parent_type == "H",
            ),
        )
        .filter(Analyzer._parent_type == "H")
        .group_by(
            Analyzer.name,
            Analyzer.model,
            Analyzer.version,
            getattr(Analyzer, "class"),
            Node.name,
            Analyzer.ostype,
            Analyzer.osversion,
        )
        .order_by(Node.name, Analyzer.name)
    )

    rows = q.all()
    
    # Group by node
    nodes_dict = defaultdict(lambda: {"name": "", "os": None, "agents": []})
    total_agents = 0

    for row in rows:
        last_hb_time = row.last_heartbeat
        if last_hb_time:
            delta = current_time - last_hb_time
            seconds = int(delta.total_seconds())
            if seconds < 60:
                rel_time = f"{seconds} seconds ago"
            elif seconds < 3600:
                rel_time = f"{seconds // 60} minutes ago"
            else:
                rel_time = f"{seconds // 3600} hours ago"
        else:
            rel_time = "No heartbeat"

        interval = row.heartbeat_interval or 600
        timeout_seconds = interval * 2
        status = "Offline"
        if last_hb_time and (current_time - last_hb_time) <= timedelta(
            seconds=timeout_seconds
        ):
            status = "Online"

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
        "Node_Name": "server-001\.example\.internal",
        "Model": "Snort"
      },
      ...
    ]
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    base_query = (
        db.query(
            AnalyzerTime.time.label("timestamp"),
            Analyzer.name.label("agent"),
            Node.name.label("node_name"),
            Address.address.label("node_address"),
            Analyzer.model.label("model"),
        )
        .join(
            Heartbeat,
            and_(
                Heartbeat._ident == AnalyzerTime._message_ident,
                AnalyzerTime._parent_type == "H",
            ),
        )
        .join(
            Analyzer,
            and_(
                Analyzer._message_ident == Heartbeat._ident,
                Analyzer._parent_type == "H",
                # you could remove this if you want *all* analyzers,
                # but let's keep it if your logic expects index=0 = primary
                Analyzer._index == 0,
            ),
        )
        .outerjoin(
            Node,
            and_(
                Node._message_ident == Heartbeat._ident,
                Node._parent_type == "H",
                Node._parent0_index == 0,
            ),
        )
        .outerjoin(
            Address,
            and_(
                Address._message_ident == Node._message_ident,
                Address._parent_type == Node._parent_type,
                Address._parent0_index == Node._parent0_index,
                Address._index == 0,
            ),
        )
        .filter(AnalyzerTime.time >= cutoff_time)
    )

    total_count = base_query.count()

    results = (
        base_query.order_by(AnalyzerTime.time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

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
