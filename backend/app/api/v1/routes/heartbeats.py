from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from datetime import datetime, timedelta
from enum import Enum

from ....database.config import get_prelude_db
from ....models.prelude import (
    Heartbeat,
    Analyzer,
    AnalyzerTime,
    Node,
    Address,
)
from ....schemas.prelude import (
    HeartbeatTreeResponse,
    HeartbeatTimelineResponse,
    TreeHostInfo,
    TreeAgentInfo,
)
#from ..routes.auth import get_current_user

router = APIRouter()
# dependencies=[Depends(get_current_user)]
class SortField(str, Enum):
    LAST_HEARTBEAT = "last_heartbeat"
    AGENT = "agent"
    STATUS = "status"

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

@router.get("/tree", response_model=HeartbeatTreeResponse)
async def list_heartbeats_tree(
    db: Session = Depends(get_prelude_db),
) -> HeartbeatTreeResponse:
    """Get the latest heartbeat for each agent for the tree view"""
    
    # First get all agents (both from alerts and heartbeats)
    agents_subq = (
        db.query(
            Node.name.label('host'),
            Analyzer.osversion,
            Analyzer.name,
            Analyzer.model,
            Analyzer.version,
            getattr(Analyzer, 'class').label('class_'),
            Analyzer._message_ident.label('message_ident'),
            AnalyzerTime.time.label('heartbeat_time'),
            Heartbeat.heartbeat_interval,
            func.row_number().over(
                partition_by=[Node.name, Analyzer.name],
                order_by=AnalyzerTime.time.desc()
            ).label('rn')
        )
        .select_from(Analyzer)
        .join(
            Node,
            and_(
                Node._message_ident == Analyzer._message_ident,
                Node._parent_type == Analyzer._parent_type
            )
        )
        .join(
            AnalyzerTime,
            and_(
                AnalyzerTime._message_ident == Analyzer._message_ident,
                AnalyzerTime._parent_type == 'H'
            ),
            isouter=True
        )
        .join(
            Heartbeat,
            Heartbeat._ident == Analyzer._message_ident,
            isouter=True
        )
        .filter(or_(Analyzer._parent_type == 'H', Analyzer._parent_type == 'A'))
        .subquery()
    )

    # Then get only the latest entry for each agent on each host
    results = (
        db.query(
            agents_subq.c.host,
            agents_subq.c.osversion,
            agents_subq.c.name,
            agents_subq.c.model,
            agents_subq.c.version,
            agents_subq.c.class_,
            agents_subq.c.heartbeat_time.label('last_heartbeat'),
            agents_subq.c.heartbeat_interval,
        )
        .select_from(agents_subq)
        .filter(agents_subq.c.rn == 1)
        .order_by(agents_subq.c.host, agents_subq.c.name)
        .all()
    )

    # Group by host
    hosts: dict[str, TreeHostInfo] = {}
    total_agents = 0
    current_time = datetime.utcnow()
    
    for r in results:
        if not r.host:
            continue  # Skip entries without host
            
        # If no heartbeat_interval is configured, use 10 minutes (600 seconds)
        timeout = timedelta(seconds=r.heartbeat_interval * 2 if r.heartbeat_interval else 600)
        # If last_heartbeat is None, the agent has never sent a heartbeat
        status = "offline" if r.last_heartbeat is None else "online" if (current_time - r.last_heartbeat) <= timeout else "offline"
        
        if r.host not in hosts:
            hosts[r.host] = TreeHostInfo(
                os=f"Linux {r.osversion}" if r.osversion else None,
                agents=[]
            )
            
        agent_info = {
            "name": r.name,
            "model": r.model,
            "version": r.version,
            "class": r.class_,
            "last_heartbeat": r.last_heartbeat,
            "status": status,
        }
        hosts[r.host].agents.append(TreeAgentInfo(**agent_info))
        total_agents += 1

    return HeartbeatTreeResponse(
        hosts=hosts,
        total_hosts=len(hosts),
        total_agents=total_agents,
    )

@router.get("/timeline", response_model=HeartbeatTimelineResponse)
async def list_heartbeats_timeline(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to show"),
    db: Session = Depends(get_prelude_db),
) -> HeartbeatTimelineResponse:
    """Get heartbeat timeline data"""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    # Optimized query with specific column selection and proper join order
    query = (
        db.query(
            AnalyzerTime.time.label('timestamp'),
            Analyzer.name.label('agent'),
            Node.name.label('node_name'),
            Address.address.label('node_address'),
            Analyzer.model,
        )
        .select_from(AnalyzerTime)
        .join(
            Heartbeat,
            and_(
                Heartbeat._ident == AnalyzerTime._message_ident,
                AnalyzerTime._parent_type == 'H'
            )
        )
        .join(
            Analyzer,
            and_(
                Analyzer._message_ident == Heartbeat._ident,
                Analyzer._parent_type == 'H',
                Analyzer._index == 0
            )
        )
        .join(
            Node,
            and_(
                Node._message_ident == Heartbeat._ident,
                Node._parent_type == 'H'
            )
        )
        .outerjoin(  # Using outer join in case some nodes don't have addresses
            Address,
            and_(
                Address._message_ident == Node._message_ident,
                Address._parent_type == Node._parent_type
            )
        )
        .filter(AnalyzerTime.time >= cutoff_time) # Apply the time filter
        .order_by(AnalyzerTime.time.desc())
    )

    total = query.count()

    results = query.all()


    items = [{
        "timestamp": r.timestamp,
        "agent": r.agent,
        "node_name": r.node_name,
        "node_address": r.node_address if r.node_address else r.node_name,  # Fallback to node_name if no address
        "model": r.model,
    } for r in results]

    return {
        "items": items,
        "total": total,
    }