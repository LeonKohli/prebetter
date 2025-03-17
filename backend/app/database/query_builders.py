"""
Query builder functions for the Prelude SIEM API.

These functions build reusable SQLAlchemy queries that can be used throughout 
the application to reduce code duplication and maintain consistent query patterns.
"""

from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_, literal_column, tuple_, text, case, literal
from datetime import datetime

from ..models.prelude import (
    Alert,
    Impact,
    Classification,
    Address,
    DetectTime,
    Analyzer,
    Node,
    Reference,
    Service,
    AdditionalData,
    CreateTime,
    Process,
    Source,
    Target,
    WebService,
    Alertident,
    AnalyzerTime,
    Heartbeat,
)
from .config import (
    get_analyzer_join_conditions,
    get_node_join_conditions,
)

def build_alert_base_query(db: Session):
    """
    Build a base query for alerts with essential joins.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        SQLAlchemy query object with all standard joins for alert listing
    """
    # Create aliases for source and target addresses
    source_addr = aliased(Address)
    target_addr = aliased(Address)

    # Base query for alerts with essential joins
    query = (
        db.query(
            Alert._ident,
            Alert.messageid,
            DetectTime.time.label("detect_time"),
            DetectTime.usec.label("detect_time_usec"),
            DetectTime.gmtoff.label("detect_time_gmtoff"),
            CreateTime.time.label("create_time"),
            CreateTime.usec.label("create_time_usec"),
            CreateTime.gmtoff.label("create_time_gmtoff"),
            Classification.text.label("classification_text"),
            Impact.severity,
            source_addr.address.label("source_ipv4"),
            target_addr.address.label("target_ipv4"),
            Analyzer.name.label("analyzer_name"),
            Node.name.label("analyzer_host"),
            Analyzer.model.label("analyzer_model"),
            Analyzer.manufacturer.label("analyzer_manufacturer"),
            Analyzer.version.label("analyzer_version"),
            literal_column("Prelude_Analyzer.class").label("analyzer_class"),
            Analyzer.ostype.label("analyzer_ostype"),
            Analyzer.osversion.label("analyzer_osversion"),
            Node.location.label("node_location"),
            Node.category.label("node_category"),
        )
        # Join DetectTime which is always required
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        # More selective left join for CreateTime to reduce unnecessary data
        .outerjoin(
            CreateTime, 
            and_(
                CreateTime._message_ident == Alert._ident, 
                CreateTime._parent_type == "A"
            )
        )
        # Join Classification which is usually required for filtering
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        # Join Impact which is usually required for severity filtering
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        # Use optimized join condition for source addresses
        .outerjoin(
            source_addr,
            and_(
                source_addr._message_ident == Alert._ident,
                source_addr._parent_type == "S",
                source_addr.category == "ipv4-addr",
            ),
        )
        # Use optimized join condition for target addresses
        .outerjoin(
            target_addr,
            and_(
                target_addr._message_ident == Alert._ident,
                target_addr._parent_type == "T",
                target_addr.category == "ipv4-addr",
            ),
        )
        # Selectively join Analyzer using the optimized conditions
        .outerjoin(
            Analyzer,
            get_analyzer_join_conditions(Alert._ident),
        )
        # Selectively join Node using the optimized conditions
        .outerjoin(
            Node,
            get_node_join_conditions(Alert._ident),
        )
    )
    
    return query, {"source_addr": source_addr, "target_addr": target_addr}


def build_alert_count_query(db: Session):
    """
    Build an optimized count query for alerts.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        SQLAlchemy query object optimized for counting alerts
    """
    # Create aliases for source and target addresses but only when needed for filtering
    source_addr = aliased(Address)
    target_addr = aliased(Address)

    # Highly optimized count query with minimal required joins
    # Only include joins that are essential for filtering
    count_query = (
        db.query(func.count(Alert._ident))
        .select_from(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        # Other joins only added as needed during filter application
        # Don't join unnecessary tables for simple counting
    )
    
    return count_query, {"source_addr": source_addr, "target_addr": target_addr}


def build_grouped_alerts_query(db: Session):
    """
    Build a query for alerts grouped by source and target IP.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        SQLAlchemy query object for grouped alerts
    """
    # Create aliases for source and target addresses
    source_addr = aliased(Address, name="source_addr")
    target_addr = aliased(Address, name="target_addr")

    # Optimized query for getting unique source-target pairs with total counts
    # Focus on efficient grouping and aggregation
    pairs_query = (
        db.query(
            source_addr.address.label("source_ipv4"),
            target_addr.address.label("target_ipv4"),
            func.count(Alert._ident).label("total_count"),
            func.max(DetectTime.time).label("latest_time"),
            func.max(Impact.severity).label("max_severity"),
            # Use group_concat for these to reduce separate queries
            func.group_concat(func.distinct(Classification.text), ',').label("latest_classification"),
            func.group_concat(func.distinct(Analyzer.name), ',').label("analyzer_name"),
        )
        .select_from(Alert)
        # Essential joins first
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        # Only include necessary joins for grouping and aggregation
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        # Efficient joins for source and target address
        .outerjoin(
            source_addr,
            and_(
                source_addr._message_ident == Alert._ident,
                source_addr._parent_type == "S",
                source_addr.category == "ipv4-addr",
            ),
        )
        .outerjoin(
            target_addr,
            and_(
                target_addr._message_ident == Alert._ident,
                target_addr._parent_type == "T",
                target_addr.category == "ipv4-addr",
            ),
        )
        # Only join analyzer when needed
        .outerjoin(
            Analyzer,
            get_analyzer_join_conditions(Alert._ident),
        )
        # Use filtering to improve performance of GROUP BY
        .filter(source_addr.address is not None)
        .filter(target_addr.address is not None)
        .group_by(
            source_addr.address,
            target_addr.address,
        )
    )
    
    return pairs_query, {"source_addr": source_addr, "target_addr": target_addr}


def build_grouped_alerts_detail_query(db: Session, pairs):
    """
    Build a query for detailed information about grouped alerts.
    
    Args:
        db: SQLAlchemy database session
        pairs: List of source-target pairs from the grouped_alerts_query
        
    Returns:
        SQLAlchemy query object for detailed information about grouped alerts
    """
    # Create aliases for source and target addresses
    source_addr = aliased(Address, name="source_addr")
    target_addr = aliased(Address, name="target_addr")

    # Optimize pairs list to limit query complexity
    # If too many pairs provided, limit to first 10 to avoid excessive query size
    limited_pairs = pairs[:10] if len(pairs) > 10 else pairs
    
    # Efficiently construct source-target pair list for IN clause
    pair_tuples = [(p.source_ipv4, p.target_ipv4) for p in limited_pairs]
    
    # Optimized alert details query with efficient joins and data retrieval
    alerts_query = (
        db.query(
            source_addr.address.label("source_ipv4"),
            target_addr.address.label("target_ipv4"),
            Classification.text.label("classification"),
            func.count(Alert._ident).label("count"),
            # Use group_concat with DISTINCT for better performance
            func.group_concat(func.distinct(Analyzer.name)).label("analyzers"),
            func.group_concat(func.distinct(Node.name)).label("analyzer_hosts"),
            func.max(DetectTime.time).label("latest_time"),
        )
        .select_from(Alert)
        # Essential joins first
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        .join(Classification, Classification._message_ident == Alert._ident)
        # Use efficient join conditions for addresses
        .join(
            source_addr,
            and_(
                source_addr._message_ident == Alert._ident,
                source_addr._parent_type == "S",
                source_addr.category == "ipv4-addr",
            ),
        )
        .join(
            target_addr,
            and_(
                target_addr._message_ident == Alert._ident,
                target_addr._parent_type == "T",
                target_addr.category == "ipv4-addr",
            ),
        )
        # Only join analyzer and node when needed
        .outerjoin(
            Analyzer,
            get_analyzer_join_conditions(Alert._ident),
        )
        .outerjoin(
            Node,
            get_node_join_conditions(Alert._ident),
        )
        # Use efficient IN clause to filter by pairs
        .filter(
            tuple_(source_addr.address, target_addr.address).in_(pair_tuples)
        )
        # Group by the main columns for aggregation
        .group_by(
            source_addr.address,
            target_addr.address,
            Classification.text
        )
    )
    
    return alerts_query, {"source_addr": source_addr, "target_addr": target_addr}


def build_alert_detail_query(db: Session, alert_id: int):
    """
    Build a query for detailed alert information.
    
    Args:
        db: SQLAlchemy database session
        alert_id: The ID of the alert to get details for
        
    Returns:
        Dict of SQLAlchemy queries for various aspects of the alert
    """
    # Get base alert information
    base_query = (
        db.query(Alert, CreateTime, DetectTime, Classification, Impact)
        .outerjoin(
            CreateTime,
            and_(
                CreateTime._message_ident == Alert._ident,
                CreateTime._parent_type == "A",
            ),
        )
        .outerjoin(DetectTime, DetectTime._message_ident == Alert._ident)
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        .filter(Alert._ident == alert_id)
    )
    
    # Get source information with complete details
    source_info_query = (
        db.query(Source, Address, Service, Node, Process)
        .outerjoin(
            Address,
            and_(
                Address._message_ident == Source._message_ident,
                Address._parent_type == "S",
                Address._parent0_index == Source._index,
            ),
        )
        .outerjoin(
            Service,
            and_(
                Service._message_ident == Source._message_ident,
                Service._parent_type == "S",
                Service._parent0_index == Source._index,
            ),
        )
        .outerjoin(
            Node,
            and_(
                Node._message_ident == Source._message_ident,
                Node._parent_type == "S",
            ),
        )
        .outerjoin(
            Process,
            and_(
                Process._message_ident == Source._message_ident,
                Process._parent_type == "H",  # Get heartbeat process info
            ),
        )
        .filter(Source._message_ident == alert_id)
    )
    
    # Get all source addresses
    source_addresses_query = (
        db.query(Address.address)
        .filter(
            Address._message_ident == alert_id,
            Address._parent_type == "S",
        )
        .distinct()
    )
    
    # Get target information with complete details
    target_info_query = (
        db.query(Target, Address, Service, Node, Process)
        .outerjoin(
            Address,
            and_(
                Address._message_ident == Target._message_ident,
                Address._parent_type == "T",
                Address._parent0_index == Target._index,
            ),
        )
        .outerjoin(
            Service,
            and_(
                Service._message_ident == Target._message_ident,
                Service._parent_type == "T",
                Service._parent0_index == Target._index,
            ),
        )
        .outerjoin(
            Node,
            and_(
                Node._message_ident == Target._message_ident,
                Node._parent_type == "T",
            ),
        )
        .outerjoin(
            Process,
            and_(
                Process._message_ident == Target._message_ident,
                Process._parent_type == "H",  # Get heartbeat process info
            ),
        )
        .filter(Target._message_ident == alert_id)
    )
    
    # Get all target addresses
    target_addresses_query = (
        db.query(Address.address)
        .filter(
            Address._message_ident == alert_id,
            Address._parent_type == "T",
        )
        .distinct()
    )
    
    # Get all analyzers in the chain with their details
    analyzers_query = (
        db.query(Analyzer, Node, Process, AnalyzerTime)
        .outerjoin(
            Node,
            and_(
                Node._message_ident == Analyzer._message_ident,
                Node._parent_type == "A",
                Node._parent0_index == Analyzer._index,
            ),
        )
        .outerjoin(
            Process,
            and_(
                Process._message_ident == Analyzer._message_ident,
                Process._parent_type == "A",
                Process._parent0_index == Analyzer._index,
            ),
        )
        .outerjoin(
            AnalyzerTime,
            and_(
                AnalyzerTime._message_ident == Analyzer._message_ident,
                AnalyzerTime._parent_type == "A",
            ),
        )
        .filter(
            Analyzer._message_ident == alert_id,
            Analyzer._parent_type == "A",
        )
        .order_by(Analyzer._index)  # Order by chain position
    )
    
    # Get references
    references_query = (
        db.query(Reference)
        .filter(Reference._message_ident == alert_id)
        .distinct()
    )
    
    # Get services
    services_query = (
        db.query(Service)
        .filter(Service._message_ident == alert_id)
        .distinct()
    )
    
    # Get web services
    web_services_query = (
        db.query(WebService)
        .filter(WebService._message_ident == alert_id)
        .distinct()
    )
    
    # Get alert idents
    alert_idents_query = (
        db.query(Alertident)
        .filter(Alertident._message_ident == alert_id)
        .distinct()
    )
    
    # Get additional data
    additional_data_query = (
        db.query(AdditionalData)
        .filter(
            AdditionalData._message_ident == alert_id,
            AdditionalData._parent_type == "A",
        )
    )
    
    return {
        "base": base_query,
        "source_info": source_info_query,
        "source_addresses": source_addresses_query,
        "target_info": target_info_query,
        "target_addresses": target_addresses_query,
        "analyzers": analyzers_query,
        "references": references_query,
        "services": services_query,
        "web_services": web_services_query,
        "alert_idents": alert_idents_query,
        "additional_data": additional_data_query,
    }


def build_alerts_timeline_query(db: Session, date_format: str):
    """
    Build a query for timeline of alerts.
    
    Args:
        db: SQLAlchemy database session
        date_format: Format string for date grouping
        
    Returns:
        SQLAlchemy query object for alert timeline
    """
    # Base query for alerts
    timeline_query = (
        db.query(
            func.date_format(DetectTime.time, date_format).label("time_bucket"),
            func.count(Alert._ident.distinct()).label("total"),
            Impact.severity,
            Classification.text.label("classification"),
            Analyzer.name.label("analyzer"),
        )
        .select_from(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        .outerjoin(
            Analyzer,
            get_analyzer_join_conditions(Alert._ident),
        )
    )
    
    return timeline_query


def build_alerts_statistics_query(db: Session, start_time: datetime, end_time: datetime):
    """
    Build queries for alert statistics.
    
    Args:
        db: SQLAlchemy database session
        start_time: Start time for statistics
        end_time: End time for statistics
        
    Returns:
        Dict of SQLAlchemy queries for various statistics
    """
    # Create aliases for source and target addresses
    source_addr = aliased(Address)
    target_addr = aliased(Address)
    
    # Base query for alerts within time range
    base_query = (
        db.query(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        .filter(DetectTime.time >= start_time)
        .filter(DetectTime.time <= end_time)
    )
    
    # Get alerts by severity
    severity_query = (
        base_query
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        .group_by(Impact.severity)
        .with_entities(Impact.severity, func.count(Alert._ident.distinct()))
    )
    
    # Get alerts by classification
    classification_query = (
        base_query
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        .group_by(Classification.text)
        .with_entities(Classification.text, func.count(Alert._ident.distinct()))
    )
    
    # Get alerts by analyzer
    analyzer_query = (
        base_query
        .outerjoin(
            Analyzer,
            get_analyzer_join_conditions(Alert._ident),
        )
        .group_by(Analyzer.name)
        .with_entities(Analyzer.name, func.count(Alert._ident.distinct()))
    )
    
    # Get top source IPs
    source_ip_query = (
        base_query
        .outerjoin(
            source_addr,
            and_(
                source_addr._message_ident == Alert._ident,
                source_addr._parent_type == "S",
                source_addr.category == "ipv4-addr",
            ),
        )
        .group_by(source_addr.address)
        .with_entities(source_addr.address, func.count(Alert._ident.distinct()))
        .order_by(func.count(Alert._ident.distinct()).desc())
        .limit(10)
    )
    
    # Get top target IPs
    target_ip_query = (
        base_query
        .outerjoin(
            target_addr,
            and_(
                target_addr._message_ident == Alert._ident,
                target_addr._parent_type == "T",
                target_addr.category == "ipv4-addr",
            ),
        )
        .group_by(target_addr.address)
        .with_entities(target_addr.address, func.count(Alert._ident.distinct()))
        .order_by(func.count(Alert._ident.distinct()).desc())
        .limit(10)
    )
    
    return {
        "base": base_query,
        "severity": severity_query,
        "classification": classification_query,
        "analyzer": analyzer_query,
        "source_ip": source_ip_query,
        "target_ip": target_ip_query,
    }


def build_heartbeats_tree_query(db: Session):
    """
    Build a query for the tree view of heartbeats.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        SQLAlchemy query object for heartbeat tree view
    """
    tree_query = (
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
    
    return tree_query


def build_heartbeats_timeline_query(db: Session, cutoff_time: datetime):
    """
    Build a query for the timeline of heartbeats.
    
    Args:
        db: SQLAlchemy database session
        cutoff_time: Cutoff time for heartbeats (show newer)
        
    Returns:
        SQLAlchemy query object for heartbeat timeline
    """
    timeline_query = (
        db.query(
            AnalyzerTime.time.label("timestamp"),
            Analyzer.name.label("analyzer_name"),
            Node.name.label("host_name"),
            Address.address.label("node_address"),
            Analyzer.model.label("model"),
            Analyzer.version.label("version"),
            getattr(Analyzer, "class").label("class_"),
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
    
    return timeline_query


def build_efficient_heartbeats_query(db: Session, days: int = 1):
    """
    Build an efficient query for heartbeats status using Common Table Expressions (CTEs).
    
    This implements the optimized query that:
    1. Gets the latest heartbeats within the specified time period
    2. Joins with analyzer and node information
    3. Calculates the online/offline status based on heartbeat time
    
    Args:
        db: SQLAlchemy database session
        days: Number of days to look back for heartbeats (default: 1)
        
    Returns:
        SQLAlchemy query object for efficient heartbeat status
    """
    # Define the cutoff time for heartbeats
    cutoff_time = func.date_sub(func.now(), text(f"INTERVAL {days} DAY"))
    
    # CTE 1: Get latest heartbeats within time period
    latest_heartbeats = (
        db.query(
            Heartbeat._ident,
            Heartbeat.messageid,
            AnalyzerTime.time.label("heartbeat_time")
        )
        .join(
            AnalyzerTime,
            and_(
                Heartbeat._ident == AnalyzerTime._message_ident,
                AnalyzerTime._parent_type == "H"
            )
        )
        .filter(AnalyzerTime.time >= cutoff_time)
        .cte("latest_heartbeats")
    )
    
    # CTE 2: Group heartbeats by host and analyzer, getting the latest time
    heartbeats = (
        db.query(
            Node.name.label("host_name"),
            Analyzer.name.label("analyzer_name"),
            func.max(latest_heartbeats.c.heartbeat_time).label("last_heartbeat")
        )
        .select_from(latest_heartbeats)
        .join(
            Analyzer,
            and_(
                Analyzer._message_ident == latest_heartbeats.c._ident,
                Analyzer._parent_type == "H"
            )
        )
        .join(
            Node,
            and_(
                Node._message_ident == latest_heartbeats.c._ident,
                Node._parent_type == "H"
            )
        )
        .group_by(Node.name, Analyzer.name)
        .cte("heartbeats")
    )
    
    # CTE 3: Get distinct analyzer information
    # Use GROUP BY to ensure we get only one entry per host+analyzer combination
    analyzers = (
        db.query(
            Node.name.label("host_name"),
            Analyzer.name.label("analyzer_name"),
            # Use first() to get a single value for each group
            func.min(Analyzer.model).label("model"),
            func.min(Analyzer.version).label("version"),
            func.min(getattr(Analyzer, "class")).label("class_"),
            # Add OS information - use min() to get a single value
            func.min(
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
                )
            ).label("os")
        )
        .select_from(Node)
        .join(
            Analyzer,
            Analyzer._message_ident == Node._message_ident
        )
        .filter(
            Node._parent_type == "A",
            Node._parent0_index == -1
        )
        # Group by host_name and analyzer_name to ensure uniqueness
        .group_by(Node.name, Analyzer.name)
        .cte("analyzers")
    )
    
    # Final query: Join the CTEs and calculate status
    # Ensure the output format exactly matches the SQL query
    final_query = (
        db.query(
            analyzers.c.host_name,
            analyzers.c.analyzer_name,
            analyzers.c.model,
            analyzers.c.version,
            analyzers.c.class_,
            analyzers.c.os,
            # Use literal 'Never' for null heartbeats to match SQL query
            func.coalesce(heartbeats.c.last_heartbeat, literal("Never")).label("last_heartbeat"),
            # Use -1 for null seconds_ago to match SQL query
            func.coalesce(
                func.timestampdiff(text("SECOND"), heartbeats.c.last_heartbeat, func.now()),
                literal(-1)
            ).label("seconds_ago"),
            # Status calculation based on seconds_ago
            case(
                (
                    func.timestampdiff(text("SECOND"), heartbeats.c.last_heartbeat, func.now()) <= 600,
                    literal("online")
                ),
                else_=literal("offline")
            ).label("status")
        )
        .select_from(analyzers)
        .outerjoin(
            heartbeats,
            and_(
                analyzers.c.host_name == heartbeats.c.host_name,
                analyzers.c.analyzer_name == heartbeats.c.analyzer_name
            )
        )
        .order_by(analyzers.c.host_name, analyzers.c.analyzer_name)
    )
    
    return final_query