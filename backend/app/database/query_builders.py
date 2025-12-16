"""
Query builder functions for the Prelude IDS API.

These functions build reusable SQLAlchemy queries that can be used throughout
the application to reduce code duplication and maintain consistent query patterns.
"""


from sqlalchemy.orm import Session, aliased
from sqlalchemy import (
    select,
    and_,
    literal_column,
    text,
)
from sqlalchemy import Table, MetaData
from sqlalchemy.exc import NoSuchTableError
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


# NOTE: _build_classification_subquery removed - moved to GroupedAlertRepository


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


# NOTE: Grouped alert query builders removed - replaced by GroupedAlertRepository:
# - _apply_grouped_filters
# - build_grouped_alerts_query
# - build_grouped_alerts_count_query
# - build_grouped_alerts_detail_query


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


# NOTE: build_alerts_timeline_query removed - replaced by AlertRepository.get_timeline()
# NOTE: build_alerts_statistics_query removed - replaced by StatisticsRepository.get_summary()


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
