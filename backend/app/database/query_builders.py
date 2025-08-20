"""
Query builder functions for the Prelude SIEM API.

These functions build reusable SQLAlchemy queries that can be used throughout
the application to reduce code duplication and maintain consistent query patterns.
"""

from sqlalchemy.orm import Session, aliased
from sqlalchemy import select, func, and_, literal_column, tuple_, text, case, literal
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging

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

logger = logging.getLogger(__name__)


def build_alert_base_query(db: Session):
    """Build a base query for alerts with essential joins."""
    source_addr = aliased(Address)
    target_addr = aliased(Address)

    query = (
        select(
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
        .select_from(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        # parent_type="A" ensures we only get alert creation times
        .outerjoin(
            CreateTime,
            and_(
                CreateTime._message_ident == Alert._ident,
                CreateTime._parent_type == "A",
            ),
        )
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
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
        .outerjoin(
            Analyzer,
            get_analyzer_join_conditions(Alert._ident),
        )
        .outerjoin(
            Node,
            get_node_join_conditions(Alert._ident),
        )
    )

    return query, {"source_addr": source_addr, "target_addr": target_addr}


def build_alert_count_query(db: Session):
    """Build an optimized count query for alerts."""
    source_addr = aliased(Address)
    target_addr = aliased(Address)

    count_query = (
        select(func.count(Alert._ident))
        .select_from(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
    )

    return count_query, {"source_addr": source_addr, "target_addr": target_addr}


def build_grouped_alerts_query(db: Session):
    """Build a query for alerts grouped by source and target IP."""
    source_addr = aliased(Address, name="source_addr")
    target_addr = aliased(Address, name="target_addr")

    pairs_query = (
        select(
            source_addr.address.label("source_ipv4"),
            target_addr.address.label("target_ipv4"),
            func.count(func.distinct(Alert._ident)).label("total_count"),
            func.max(DetectTime.time).label("latest_time"),
            func.max(Impact.severity).label("max_severity"),
            # GROUP_CONCAT aggregates string values efficiently
            func.group_concat(func.distinct(Classification.text), ",").label(
                "latest_classification"
            ),
            func.group_concat(func.distinct(Analyzer.name), ",").label("analyzer_name"),
        )
        .select_from(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
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
        .outerjoin(
            Analyzer,
            get_analyzer_join_conditions(Alert._ident),
        )
        .where(source_addr.address.isnot(None))
        .where(target_addr.address.isnot(None))
        .group_by(
            source_addr.address,
            target_addr.address,
        )
    )

    return pairs_query, {"source_addr": source_addr, "target_addr": target_addr}


def build_grouped_alerts_detail_query(db: Session, pairs):
    """Build a query for detailed information about grouped alerts."""
    source_addr = aliased(Address, name="source_addr")
    target_addr = aliased(Address, name="target_addr")

    pair_tuples = [(p.source_ipv4, p.target_ipv4) for p in pairs]

    alerts_query = (
        select(
            source_addr.address.label("source_ipv4"),
            target_addr.address.label("target_ipv4"),
            Classification.text.label("classification"),
            func.count(func.distinct(Alert._ident)).label("count"),
            # Use group_concat with DISTINCT for better performance
            func.group_concat(func.distinct(Analyzer.name)).label("analyzers"),
            func.group_concat(func.distinct(Node.name)).label("analyzer_hosts"),
            func.max(DetectTime.time).label("latest_time"),
        )
        .select_from(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
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
        .outerjoin(
            Analyzer,
            get_analyzer_join_conditions(Alert._ident),
        )
        .outerjoin(
            Node,
            get_node_join_conditions(Alert._ident),
        )
        # tuple_ matches multiple columns efficiently
        .where(tuple_(source_addr.address, target_addr.address).in_(pair_tuples))
        .group_by(source_addr.address, target_addr.address, Classification.text)
    )

    return alerts_query, {"source_addr": source_addr, "target_addr": target_addr}


def build_alert_detail_query(db: Session, alert_id: int):
    """Build queries for detailed alert information (avoids cartesian products)."""
    base_query = (
        select(Alert, CreateTime, DetectTime, Classification, Impact)
        .select_from(Alert)
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
        .where(Alert._ident == alert_id)
    )

    source_info_query = (
        select(Source, Address, Service, Node, Process)
        .select_from(Source)
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
                Process._parent_type == "H",  # From heartbeat messages
            ),
        )
        .where(Source._message_ident == alert_id)
    )

    source_addresses_query = (
        select(Address.address)
        .where(
            Address._message_ident == alert_id,
            Address._parent_type == "S",
        )
        .distinct()
    )

    target_info_query = (
        select(Target, Address, Service, Node, Process)
        .select_from(Target)
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
                Process._parent_type == "H",  # From heartbeat messages
            ),
        )
        .where(Target._message_ident == alert_id)
    )

    target_addresses_query = (
        select(Address.address)
        .where(
            Address._message_ident == alert_id,
            Address._parent_type == "T",
        )
        .distinct()
    )

    analyzers_query = (
        select(Analyzer, Node, Process, AnalyzerTime)
        .select_from(Analyzer)
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
        .where(
            Analyzer._message_ident == alert_id,
            Analyzer._parent_type == "A",
        )
        .order_by(Analyzer._index)
    )

    references_query = (
        select(Reference).where(Reference._message_ident == alert_id).distinct()
    )

    services_query = (
        select(Service).where(Service._message_ident == alert_id).distinct()
    )

    web_services_query = (
        select(WebService).where(WebService._message_ident == alert_id).distinct()
    )

    alert_idents_query = (
        select(Alertident).where(Alertident._message_ident == alert_id).distinct()
    )

    additional_data_query = select(AdditionalData).where(
        AdditionalData._message_ident == alert_id,
        AdditionalData._parent_type == "A",
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
    """Build a query for timeline of alerts."""
    timeline_query = (
        select(
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


def build_alerts_statistics_query(
    db: Session, start_time: datetime, end_time: datetime
):
    """Build queries for alert statistics."""
    source_addr = aliased(Address)
    target_addr = aliased(Address)

    base_query = (
        select(Alert)
        .select_from(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        .where(DetectTime.time >= start_time)
        .where(DetectTime.time <= end_time)
    )

    severity_query = (
        select(Impact.severity, func.count(Alert._ident.distinct()))
        .select_from(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        .where(DetectTime.time >= start_time)
        .where(DetectTime.time <= end_time)
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        .group_by(Impact.severity)
    )

    classification_query = (
        base_query.outerjoin(
            Classification, Classification._message_ident == Alert._ident
        )
        .group_by(Classification.text)
        .with_entities(Classification.text, func.count(Alert._ident.distinct()))
    )

    analyzer_query = (
        base_query.outerjoin(
            Analyzer,
            get_analyzer_join_conditions(Alert._ident),
        )
        .group_by(Analyzer.name)
        .with_entities(Analyzer.name, func.count(Alert._ident.distinct()))
    )

    source_ip_query = (
        base_query.outerjoin(
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

    target_ip_query = (
        base_query.outerjoin(
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
    """Build a query for the tree view of heartbeats."""
    tree_query = (
        db.query(
            Analyzer.name.label("name"),
            Analyzer.model.label("model"),
            Analyzer.version.label("version"),
            getattr(Analyzer, "class").label("class_"),
            Node.name.label("node_name"),
            case(
                (
                    Analyzer.ostype.isnot(None),
                    func.concat(
                        Analyzer.ostype,
                        literal(" "),
                        func.ifnull(Analyzer.osversion, literal("")),
                    ),
                ),
                else_=None,
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
    """Build a query for the timeline of heartbeats."""
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
    """Build an efficient query for heartbeats showing all analyzers from alerts."""
    # Raw SQL for performance - complex self-joins are more efficient than ORM
    sql = text("""
    SELECT 
        all_analyzers.host_name,
        all_analyzers.analyzer_name,
        all_analyzers.model,
        all_analyzers.version,
        all_analyzers.class,
        all_analyzers.os,
        COALESCE(DATE_FORMAT(heartbeats.last_heartbeat, '%Y-%m-%d %H:%i:%s'), 'Never') as last_heartbeat,
        COALESCE(TIMESTAMPDIFF(SECOND, heartbeats.last_heartbeat, NOW()), -1) as seconds_ago,
        CASE 
            # 60000 seconds threshold accounts for network issues
            WHEN heartbeats.last_heartbeat IS NOT NULL 
                AND TIMESTAMPDIFF(SECOND, heartbeats.last_heartbeat, NOW()) <= 60000 
            THEN 'online'
            ELSE 'offline'
        END as status
    FROM (
        SELECT DISTINCT 
            n.name as host_name,
            a.name as analyzer_name,
            MAX(a.model) as model,
            MAX(a.version) as version,
            MAX(a.class) as class,
            MAX(CONCAT(IFNULL(a.ostype, ''), ' ', IFNULL(a.osversion, ''))) as os
        FROM Prelude_Analyzer a
        INNER JOIN Prelude_Node n 
            ON n._message_ident = a._message_ident
            AND n._parent_type = 'A'
            AND n._parent0_index = -1
        WHERE a._parent_type = 'A'
        GROUP BY n.name, a.name
    ) AS all_analyzers
    LEFT JOIN (
        SELECT 
            n.name as host_name,
            a.name as analyzer_name,
            MAX(at.time) as last_heartbeat
        FROM Prelude_Heartbeat h
        INNER JOIN Prelude_AnalyzerTime at 
            ON at._message_ident = h._ident
            AND at.time >= DATE_SUB(NOW(), INTERVAL :days DAY)
        INNER JOIN Prelude_Analyzer a 
            ON a._message_ident = h._ident
            AND a._parent_type = 'H'
        INNER JOIN Prelude_Node n 
            ON n._message_ident = h._ident
            AND n._parent_type = 'H'
        GROUP BY n.name, a.name
    ) AS heartbeats 
        ON all_analyzers.host_name = heartbeats.host_name 
        AND all_analyzers.analyzer_name = heartbeats.analyzer_name
    ORDER BY all_analyzers.host_name, all_analyzers.analyzer_name
    """)

    try:
        return db.execute(sql, {"days": days})
    except SQLAlchemyError as e:
        logger.error(f"Error executing heartbeats query: {str(e)}")
        raise
