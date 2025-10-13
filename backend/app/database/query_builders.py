"""
Query builder functions for the Prelude IDS API.

These functions build reusable SQLAlchemy queries that can be used throughout
the application to reduce code duplication and maintain consistent query patterns.
"""

from sqlalchemy.orm import Session, aliased
from sqlalchemy import (
    select,
    func,
    and_,
    literal_column,
    text,
    case,
    literal,
)
from sqlalchemy import Table, MetaData
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
    ProcessArg,
    ProcessEnv,
)
from .config import (
    get_analyzer_join_conditions,
    get_node_join_conditions,
)

logger = logging.getLogger(__name__)

_PAIR_TABLE = None  # cache for reflected Prebetter_Pair Table


def _get_prebetter_pair_table(db: Session):
    """Reflect Prebetter_Pair if present; cache result for this process."""
    global _PAIR_TABLE
    if _PAIR_TABLE is not None:
        return _PAIR_TABLE
    try:
        metadata = MetaData()
        _PAIR_TABLE = Table("Prebetter_Pair", metadata, autoload_with=db.get_bind())
        return _PAIR_TABLE
    except Exception:
        _PAIR_TABLE = None
        return None


def _canonical_source_join(alert_alias, alias_name: str = "source"):
    """Return the canonical Source alias (index 0) and join condition."""

    source_alias = aliased(Source, name=alias_name)
    join_condition = and_(
        source_alias._message_ident == alert_alias._ident,
        source_alias._index == 0,
    )
    return source_alias, join_condition


def _canonical_target_join(alert_alias, alias_name: str = "target"):
    """Return the canonical Target alias (index 0) and join condition."""

    target_alias = aliased(Target, name=alias_name)
    join_condition = and_(
        target_alias._message_ident == alert_alias._ident,
        target_alias._index == 0,
    )
    return target_alias, join_condition


def build_alert_base_query(db: Session):
    """Build a base query for alerts with essential joins."""
    source_addr = aliased(Address)
    target_addr = aliased(Address)

    query = (
        select(
            Alert._ident,
            Alert.messageid,
            # Apply timezone conversion directly in SQL (all data is CEST/gmtoff=7200)
            func.timestampadd(text("SECOND"), DetectTime.gmtoff, DetectTime.time).label(
                "detect_time"
            ),
            func.timestampadd(text("SECOND"), CreateTime.gmtoff, CreateTime.time).label(
                "create_time"
            ),
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
        .distinct()
        .select_from(Alert)
        .outerjoin(DetectTime, Alert._ident == DetectTime._message_ident)
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


def build_grouped_alerts_query(
    db: Session,
    *,
    include_classification: bool = False,
    include_analyzer: bool = False,
    include_impact: bool = False,
):
    """Build a query for alerts grouped by canonical source and target IP.

    The query is kept lean by default. Optional joins are added only when
    required for filters or sorting to avoid row multiplication and expensive
    aggregates in the hot path.
    """

    pair_table = _get_prebetter_pair_table(db)
    if pair_table is not None:
        select_cols = [
            func.inet_ntoa(pair_table.c.source_ip).label("source_ipv4"),
            func.inet_ntoa(pair_table.c.target_ip).label("target_ipv4"),
            func.timestampadd(
                text("SECOND"), func.max(DetectTime.gmtoff), func.max(DetectTime.time)
            ).label("latest_time"),
            func.count().label("total_count"),
        ]
        if include_impact:
            select_cols.append(func.max(Impact.severity).label("max_severity"))

        pairs_query = (
            select(*select_cols)
            .select_from(DetectTime)
            .join(pair_table, pair_table.c._message_ident == DetectTime._message_ident)
        )
        if include_impact:
            pairs_query = pairs_query.outerjoin(
                Impact, Impact._message_ident == DetectTime._message_ident
            )
        if include_classification:
            pairs_query = pairs_query.outerjoin(
                Classification,
                Classification._message_ident == DetectTime._message_ident,
            )
        if include_analyzer:
            pairs_query = pairs_query.outerjoin(
                Analyzer,
                and_(
                    Analyzer._message_ident == DetectTime._message_ident,
                    Analyzer._parent_type == "A",
                ),
            )

        pairs_query = pairs_query.group_by(pair_table.c.pair_key)

        return pairs_query, {
            "pair": pair_table,
            "source_ip_order_col": func.inet_ntoa(pair_table.c.source_ip),
            "target_ip_order_col": func.inet_ntoa(pair_table.c.target_ip),
            "source_ip_int_col": pair_table.c.source_ip,
            "target_ip_int_col": pair_table.c.target_ip,
        }
    else:
        raise RuntimeError(
            "Prebetter_Pair accelerator missing. Install it before starting the API."
        )


def build_grouped_alerts_count_query(
    db: Session,
    *,
    include_classification: bool = False,
    include_analyzer: bool = False,
    include_impact: bool = False,
):
    """Build a lightweight count query for grouped alerts pagination.

    Optional joins are added only when they are needed for filters.
    """

    pair_table = _get_prebetter_pair_table(db)
    if pair_table is not None:
        count_query = (
            select(func.count(func.distinct(pair_table.c.pair_key)))
            .select_from(DetectTime)
            .join(pair_table, pair_table.c._message_ident == DetectTime._message_ident)
        )
        if include_impact:
            count_query = count_query.outerjoin(
                Impact, Impact._message_ident == DetectTime._message_ident
            )
        if include_classification:
            count_query = count_query.outerjoin(
                Classification,
                Classification._message_ident == DetectTime._message_ident,
            )
        if include_analyzer:
            count_query = count_query.outerjoin(
                Analyzer, get_analyzer_join_conditions(DetectTime._message_ident)
            )
        return count_query, {
            "pair": pair_table,
            "source_ip_int_col": pair_table.c.source_ip,
            "target_ip_int_col": pair_table.c.target_ip,
        }

    # No fallback allowed: enforce accelerator presence
    else:
        raise RuntimeError(
            "Prebetter_Pair accelerator missing. Install it before starting the API."
        )


def build_grouped_alerts_detail_query(db: Session, pairs):
    """Build a query for detailed information about grouped alerts.

    Uses Prebetter_Pair when available to avoid Address joins and tuple IN.
    Falls back to DetectTime + Address joins otherwise.
    """
    pair_table = _get_prebetter_pair_table(db)
    if pair_table is not None:
        # Compute pair_key list from provided pairs
        import ipaddress

        def ip_to_int(ip: str) -> int:
            return int(ipaddress.IPv4Address(ip))

        pair_keys = [
            (ip_to_int(p.source_ipv4) << 32) + ip_to_int(p.target_ipv4) for p in pairs
        ]

        alerts_query = (
            select(
                func.inet_ntoa(pair_table.c.source_ip).label("source_ipv4"),
                func.inet_ntoa(pair_table.c.target_ip).label("target_ipv4"),
                Classification.text.label("classification"),
                func.count().label("count"),
                func.group_concat(func.distinct(Analyzer.name)).label("analyzers"),
                literal(None).label("analyzer_hosts"),
                func.timestampadd(
                    text("SECOND"),
                    func.max(DetectTime.gmtoff),
                    func.max(DetectTime.time),
                ).label("latest_time"),
            )
            .select_from(DetectTime)
            .join(pair_table, pair_table.c._message_ident == DetectTime._message_ident)
            .outerjoin(
                Classification,
                Classification._message_ident == DetectTime._message_ident,
            )
            .outerjoin(
                Analyzer,
                and_(
                    Analyzer._message_ident == DetectTime._message_ident,
                    Analyzer._parent_type == "A",
                ),
            )
            .where(
                pair_table.c.pair_key.in_(pair_keys) if pair_keys else literal(False)
            )
            .group_by(pair_table.c.pair_key, Classification.text)
        )

        return alerts_query, {
            "pair": pair_table,
            "source_ip_int_col": pair_table.c.source_ip,
            "target_ip_int_col": pair_table.c.target_ip,
        }

    else:
        raise RuntimeError(
            "Prebetter_Pair accelerator missing. Install it before starting the API."
        )


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

    # Eagerly load all ProcessArgs and ProcessEnvs for all analyzers to avoid N+1
    process_args_query = (
        select(ProcessArg._parent0_index, ProcessArg.arg, ProcessArg._index)
        .where(
            ProcessArg._message_ident == alert_id,
            ProcessArg._parent_type == "A",
        )
        .order_by(ProcessArg._parent0_index, ProcessArg._index)
    )

    process_envs_query = (
        select(ProcessEnv._parent0_index, ProcessEnv.env, ProcessEnv._index)
        .where(
            ProcessEnv._message_ident == alert_id,
            ProcessEnv._parent_type == "A",
        )
        .order_by(ProcessEnv._parent0_index, ProcessEnv._index)
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
        "process_args": process_args_query,
        "process_envs": process_envs_query,
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
        select(Classification.text, func.count(Alert._ident.distinct()))
        .select_from(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        .where(DetectTime.time >= start_time)
        .where(DetectTime.time <= end_time)
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        .group_by(Classification.text)
    )

    analyzer_query = (
        select(Analyzer.name, func.count(Alert._ident.distinct()))
        .select_from(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        .where(DetectTime.time >= start_time)
        .where(DetectTime.time <= end_time)
        .outerjoin(
            Analyzer,
            get_analyzer_join_conditions(Alert._ident),
        )
        .group_by(Analyzer.name)
    )

    source_ip_query = (
        select(source_addr.address, func.count(Alert._ident.distinct()))
        .select_from(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        .where(DetectTime.time >= start_time)
        .where(DetectTime.time <= end_time)
        .outerjoin(
            source_addr,
            and_(
                source_addr._message_ident == Alert._ident,
                source_addr._parent_type == "S",
                source_addr.category == "ipv4-addr",
            ),
        )
        .group_by(source_addr.address)
        .order_by(func.count(Alert._ident.distinct()).desc())
        .limit(10)
    )

    target_ip_query = (
        select(target_addr.address, func.count(Alert._ident.distinct()))
        .select_from(Alert)
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        .where(DetectTime.time >= start_time)
        .where(DetectTime.time <= end_time)
        .outerjoin(
            target_addr,
            and_(
                target_addr._message_ident == Alert._ident,
                target_addr._parent_type == "T",
                target_addr.category == "ipv4-addr",
            ),
        )
        .group_by(target_addr.address)
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
        select(
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
        .where(Analyzer._parent_type == "H")
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
        select(
            AnalyzerTime.time.label("timestamp"),
            Analyzer.name.label("analyzer_name"),
            Node.name.label("host_name"),
            Address.address.label("node_address"),
            Analyzer.model.label("model"),
            Analyzer.version.label("version"),
            getattr(Analyzer, "class").label("class_"),
        )
        .distinct()  # Add DISTINCT to prevent duplicates
        .select_from(AnalyzerTime)
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
                Analyzer._index == -1,  # Use -1 to get the actual sender, not the relay
            ),
        )
        .outerjoin(
            Node,
            and_(
                Node._message_ident == Heartbeat._ident,
                Node._parent_type == "H",
                Node._parent0_index == -1,  # Match the analyzer index
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
        .where(AnalyzerTime.time >= cutoff_time)
    )

    return timeline_query


def build_efficient_heartbeats_query(db: Session, days: int = 1):
    """Build an efficient query for heartbeats showing all analyzers that have sent heartbeats."""
    # Raw SQL for performance - list all analyzers under heartbeat messages,
    # and compute their latest heartbeat (if any). Use LEFT JOIN for at to
    # include agents without events in the window.
    sql = text("""
    SELECT
        n.name as host_name,
        a.name as analyzer_name,
        MAX(a.model) as model,
        MAX(a.version) as version,
        MAX(a.class) as class,
        MAX(CONCAT(IFNULL(a.ostype, ''), ' ', IFNULL(a.osversion, ''))) as os,
        MAX(at.time) as last_heartbeat,
        MAX(h.heartbeat_interval) as heartbeat_interval
    FROM Prelude_Heartbeat h
    LEFT JOIN Prelude_AnalyzerTime at
        ON at._message_ident = h._ident
        AND at._parent_type = 'H'
    INNER JOIN Prelude_Analyzer a
        ON a._message_ident = h._ident
        AND a._parent_type = 'H'
    INNER JOIN Prelude_Node n
        ON n._message_ident = h._ident
        AND n._parent_type = 'H'
    GROUP BY n.name, a.name
    ORDER BY n.name, a.name
    """)

    # No bound parameters needed (LEFT JOIN includes agents with no recent events)
    return sql
