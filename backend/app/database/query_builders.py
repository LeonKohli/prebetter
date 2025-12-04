"""
Query builder functions for the Prelude IDS API.

These functions build reusable SQLAlchemy queries that can be used throughout
the application to reduce code duplication and maintain consistent query patterns.
"""

from typing import Optional

from sqlalchemy.orm import Session, aliased
from sqlalchemy import (
    select,
    func,
    and_,
    literal_column,
    text,
    literal,
)
from sqlalchemy import Table, MetaData
from sqlalchemy.exc import NoSuchTableError
from datetime import datetime
import ipaddress

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
    CorrelationAlert,
)
from .config import (
    get_analyzer_join_conditions,
    get_node_join_conditions,
)

# Cache for reflected Prebetter_Pair table. Reflection occurs once per process.
_PAIR_TABLE = None
_PAIR_TABLE_MISSING = False


def _build_classification_subquery(classification: str):
    """Build a subquery for classification filter supporting comma-separated values."""
    classification_list = [c.strip() for c in classification.split(",") if c.strip()]
    if len(classification_list) == 1:
        return select(Classification._message_ident).where(
            Classification.text == classification_list[0]
        )
    else:
        return select(Classification._message_ident).where(
            Classification.text.in_(classification_list)
        )


# NOTE: These globals are accessed without locks. This is acceptable because:
# 1. The Table object is immutable once created
# 2. Python's GIL makes simple assignment atomic
# 3. Worst case of race condition = redundant reflection (benign)
# 4. If table is missing, callers raise RuntimeError anyway
# Restart the app if Prebetter_Pair is added after startup.


def _get_prebetter_pair_table(db: Session):
    """Reflect Prebetter_Pair if present; cache result for this process.

    Returns the reflected Table object, or None if the table doesn't exist.
    Raises exceptions for actual DB errors (connection issues, etc.).

    Note: Requires app restart if table is created after first check.
    """
    global _PAIR_TABLE, _PAIR_TABLE_MISSING

    if _PAIR_TABLE is not None:
        return _PAIR_TABLE
    if _PAIR_TABLE_MISSING:
        return None

    metadata = MetaData()
    bind = db.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind

    try:
        _PAIR_TABLE = Table("Prebetter_Pair", metadata, autoload_with=engine)
        return _PAIR_TABLE
    except NoSuchTableError:
        # Table doesn't exist - this is expected if accelerator not installed
        _PAIR_TABLE_MISSING = True
        return None
    # Other exceptions (connection errors, etc.) propagate up


def build_alert_base_query(db: Session):
    """Build a base query for alerts with essential joins."""
    source_addr = aliased(Address)
    target_addr = aliased(Address)

    query = (
        select(
            Alert._ident,
            Alert.messageid,
            # Return UTC timestamps directly (gmtoff stored for reference but not applied)
            DetectTime.time.label("detect_time"),
            CreateTime.time.label("create_time"),
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
            CorrelationAlert.name.label("correlation_description"),
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
        .outerjoin(CorrelationAlert, CorrelationAlert._message_ident == Alert._ident)
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

    return query, {"source_addr": source_addr, "target_addr": target_addr, "Node": Node}


def _apply_grouped_filters(
    query,
    pair_table,
    *,
    start_date,
    end_date,
    source_ip,
    target_ip,
    severity,
    classification,
    analyzer_model,
):
    """Apply common filters for grouped alert queries.

    Uses subquery pattern for analyzer filter which is ~26% faster than JOIN
    because it allows MySQL to use semi-join optimization.
    """
    # Date filters
    if start_date:
        query = query.where(DetectTime.time >= start_date)
    if end_date:
        query = query.where(DetectTime.time <= end_date)

    # IP filters
    if source_ip:
        query = query.where(pair_table.c.source_ip == func.inet_aton(source_ip))
    if target_ip:
        query = query.where(pair_table.c.target_ip == func.inet_aton(target_ip))

    # Severity filter - use subquery to avoid Cartesian product
    if severity:
        severity_subq = select(Impact._message_ident).where(Impact.severity == severity)
        query = query.where(pair_table.c._message_ident.in_(severity_subq))

    # Classification filter - use subquery for semi-join optimization
    if classification:
        classification_subq = _build_classification_subquery(classification)
        query = query.where(pair_table.c._message_ident.in_(classification_subq))

    # Analyzer filter - now filters by Node.name (server) instead of Analyzer.name
    # Uses subquery for better performance (semi-join optimization)
    if analyzer_model:
        analyzer_list = [a.strip() for a in analyzer_model.split(",") if a.strip()]
        # Build subquery that joins Analyzer -> Node and filters by short node name
        analyzer_subq = (
            select(Analyzer._message_ident)
            .select_from(Analyzer)
            .outerjoin(
                Node,
                and_(
                    Node._message_ident == Analyzer._message_ident,
                    Node._parent_type == "A",
                    Node._parent0_index == Analyzer._index,
                ),
            )
            .where(Analyzer._parent_type == "A")
        )
        # Filter by short node name - match beginning of FQDN
        if len(analyzer_list) == 1:
            analyzer_subq = analyzer_subq.where(
                Node.name.startswith(analyzer_list[0] + ".")
            )
        else:
            # For multiple values, use OR conditions
            from sqlalchemy import or_

            conditions = [Node.name.startswith(a + ".") for a in analyzer_list]
            analyzer_subq = analyzer_subq.where(or_(*conditions))
        query = query.where(pair_table.c._message_ident.in_(analyzer_subq))

    return query


def build_grouped_alerts_query(
    db: Session,
    *,
    analyzer_model: Optional[str] = None,
    severity: Optional[str] = None,
    classification: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    source_ip: Optional[str] = None,
    target_ip: Optional[str] = None,
    sort_by_severity: bool = False,
    sort_by_classification: bool = False,
    sort_by_analyzer: bool = False,
):
    """Build query for alerts grouped by source/target IP pair.

    Returns (query, sort_cols) where sort_cols maps sort field names to columns.

    Args:
        sort_by_severity: Include max_severity column for sorting
        sort_by_classification: Include max_classification column for sorting
        sort_by_analyzer: Include max_analyzer column for sorting
    """
    pair_table = _get_prebetter_pair_table(db)
    if pair_table is None:
        raise RuntimeError("Prebetter_Pair accelerator missing.")

    # Build SELECT columns
    select_cols = [
        func.inet_ntoa(pair_table.c.source_ip).label("source_ipv4"),
        func.inet_ntoa(pair_table.c.target_ip).label("target_ipv4"),
        func.max(DetectTime.time).label("latest_time"),
    ]

    query = (
        select(*select_cols)
        .select_from(DetectTime)
        .join(pair_table, pair_table.c._message_ident == DetectTime._message_ident)
    )

    # Apply common filters (including classification now!)
    query = _apply_grouped_filters(
        query,
        pair_table,
        start_date=start_date,
        end_date=end_date,
        source_ip=source_ip,
        target_ip=target_ip,
        severity=severity,
        classification=classification,
        analyzer_model=analyzer_model,
    )

    # Track which columns we've added for sort_cols dict
    sort_cols = {
        "latest_time": literal_column("latest_time"),
        "source_ip": literal_column("source_ipv4"),
        "target_ip": literal_column("target_ipv4"),
        "max_severity": None,
        "max_classification": None,
        "max_analyzer": None,
    }

    classification_list = (
        [c.strip() for c in classification.split(",") if c.strip()]
        if classification
        else None
    )

    # Add severity column for sorting (uses OUTER JOIN - no Cartesian with subquery filter)
    if sort_by_severity:
        query = query.add_columns(func.max(Impact.severity).label("max_severity"))
        query = query.outerjoin(
            Impact, Impact._message_ident == DetectTime._message_ident
        )
        sort_cols["max_severity"] = literal_column("max_severity")

    # Add classification column for sorting
    if sort_by_classification:
        query = query.add_columns(
            func.max(Classification.text).label("max_classification")
        )
        join_condition = Classification._message_ident == DetectTime._message_ident
        if classification_list:
            if len(classification_list) == 1:
                join_condition = and_(
                    join_condition, Classification.text == classification_list[0]
                )
            else:
                join_condition = and_(
                    join_condition, Classification.text.in_(classification_list)
                )
        query = query.outerjoin(Classification, join_condition)
        sort_cols["max_classification"] = literal_column("max_classification")

    # Add analyzer column for sorting (using Node.name for server-based display)
    if sort_by_analyzer:
        query = query.add_columns(func.max(Node.name).label("max_analyzer"))
        analyzer_join_condition = and_(
            Analyzer._message_ident == DetectTime._message_ident,
            Analyzer._parent_type == "A",
        )
        node_join_condition = and_(
            Node._message_ident == Analyzer._message_ident,
            Node._parent_type == "A",
            Node._parent0_index == Analyzer._index,
        )
        if analyzer_model:
            analyzer_list = [a.strip() for a in analyzer_model.split(",") if a.strip()]
            if len(analyzer_list) == 1:
                node_join_condition = and_(
                    node_join_condition, Node.name.startswith(analyzer_list[0] + ".")
                )
            else:
                from sqlalchemy import or_

                conditions = [Node.name.startswith(a + ".") for a in analyzer_list]
                node_join_condition = and_(node_join_condition, or_(*conditions))
        query = query.outerjoin(Analyzer, analyzer_join_condition)
        query = query.outerjoin(Node, node_join_condition)
        sort_cols["max_analyzer"] = literal_column("max_analyzer")

    needs_distinct_count = sort_by_classification or sort_by_analyzer
    count_column = (
        func.count(func.distinct(pair_table.c._message_ident))
        if needs_distinct_count
        else func.count()
    )

    query = query.add_columns(count_column.label("total_count"))
    sort_cols["total_count"] = literal_column("total_count")

    query = query.group_by(pair_table.c.pair_key)

    return query, sort_cols


def build_grouped_alerts_count_query(
    db: Session,
    *,
    analyzer_model: Optional[str] = None,
    severity: Optional[str] = None,
    classification: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    source_ip: Optional[str] = None,
    target_ip: Optional[str] = None,
):
    """Build count query for grouped alerts pagination."""
    pair_table = _get_prebetter_pair_table(db)
    if pair_table is None:
        raise RuntimeError("Prebetter_Pair accelerator missing.")

    query = (
        select(func.count(func.distinct(pair_table.c.pair_key)))
        .select_from(DetectTime)
        .join(pair_table, pair_table.c._message_ident == DetectTime._message_ident)
    )

    # Apply same filters as main query - ensures consistent counts
    query = _apply_grouped_filters(
        query,
        pair_table,
        start_date=start_date,
        end_date=end_date,
        source_ip=source_ip,
        target_ip=target_ip,
        severity=severity,
        classification=classification,
        analyzer_model=analyzer_model,
    )

    return query


def build_grouped_alerts_detail_query(db: Session, pairs):
    """Build a query for detailed information about grouped alerts.

    Uses Prebetter_Pair when available to avoid Address joins and tuple IN.
    Falls back to DetectTime + Address joins otherwise.
    """
    pair_table = _get_prebetter_pair_table(db)
    if pair_table is not None:
        # Compute pair_key list from provided pairs
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
                func.count(func.distinct(pair_table.c._message_ident)).label("count"),
                func.group_concat(func.distinct(Analyzer.name)).label("analyzers"),
                literal(None).label("analyzer_hosts"),
                func.max(DetectTime.time).label("latest_time"),
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
        select(Alert, CreateTime, DetectTime, Classification, Impact, CorrelationAlert)
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
        .outerjoin(CorrelationAlert, CorrelationAlert._message_ident == Alert._ident)
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
    # Raw SQL for performance - shows all analyzers with recent heartbeats
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
    INNER JOIN Prelude_AnalyzerTime at
        ON at._message_ident = h._ident
        AND at._parent_type = 'H'
        AND at.time >= DATE_SUB(NOW(), INTERVAL :days DAY)
    INNER JOIN Prelude_Analyzer a
        ON a._message_ident = h._ident
        AND a._parent_type = 'H'
    INNER JOIN Prelude_Node n
        ON n._message_ident = h._ident
        AND n._parent_type = 'H'
    GROUP BY n.name, a.name
    ORDER BY n.name, a.name
    """)

    # Return the text query with parameters bound
    return sql.bindparams(days=days)
