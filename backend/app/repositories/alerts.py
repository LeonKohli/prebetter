"""
Alert Repository - Data access layer for alerts.

Encapsulates ALL alert query logic. Routes never touch SQLAlchemy directly.
Filter logic lives in ONE place - no more scattered apply_* functions.

Usage:
    repo = AlertRepository(db)
    alerts = repo.get_list(filters, pagination)
"""

import ipaddress
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session, aliased
from sqlalchemy import select, func, and_, literal_column, literal, or_, text, Table, MetaData
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.engine import Engine

from .base import BaseRepository
from app.schemas.filters import AlertFilterParams, PaginationParams
from app.models.prelude import (
    Alert,
    Impact,
    Classification,
    Address,
    DetectTime,
    Analyzer,
    Node,
    CreateTime,
    CorrelationAlert,
)
from app.database.config import (
    get_analyzer_join_conditions,
    get_node_join_conditions,
    get_prelude_db,
)
from app.core.datetime_utils import get_current_time, ensure_timezone


def reflect_pair_table(engine: Engine) -> Table | None:
    """
    Reflect Prebetter_Pair table from database.

    Called ONCE at startup in lifespan, result stored in app.state.
    Returns None if table doesn't exist (not an error - optional accelerator).
    """
    metadata = MetaData()
    try:
        return Table("Prebetter_Pair", metadata, autoload_with=engine)
    except NoSuchTableError:
        return None


class AlertRepository(BaseRepository[Alert]):
    """
    Repository for alert data access.

    All query building and filtering is encapsulated here.
    No magic **kwargs, no leaky abstractions.
    """

    def __init__(self, db: Session):
        super().__init__(db)
        # Create aliased tables once for reuse
        self._source_addr = aliased(Address)
        self._target_addr = aliased(Address)

    # =========================================================================
    # PRIVATE: Query Building
    # =========================================================================

    def _build_base_select(self):
        """
        Build base SELECT columns for alert list queries.

        Returns columns needed for AlertListItem response.
        """
        return select(
            Alert._ident,
            Alert.messageid,
            DetectTime.time.label("detect_time"),
            CreateTime.time.label("create_time"),
            Classification.text.label("classification_text"),
            Impact.severity,
            self._source_addr.address.label("source_ipv4"),
            self._target_addr.address.label("target_ipv4"),
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
        ).distinct()

    def _build_base_joins(self, query):
        """
        Apply standard JOINs for alert queries.

        All join conditions are defined HERE - single source of truth.
        """
        return (
            query.select_from(Alert)
            .outerjoin(DetectTime, Alert._ident == DetectTime._message_ident)
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
                self._source_addr,
                and_(
                    self._source_addr._message_ident == Alert._ident,
                    self._source_addr._parent_type == "S",
                    self._source_addr.category == "ipv4-addr",
                ),
            )
            .outerjoin(
                self._target_addr,
                and_(
                    self._target_addr._message_ident == Alert._ident,
                    self._target_addr._parent_type == "T",
                    self._target_addr.category == "ipv4-addr",
                ),
            )
            .outerjoin(Analyzer, get_analyzer_join_conditions(Alert._ident))
            .outerjoin(Node, get_node_join_conditions(Alert._ident))
        )

    def _apply_filters(
        self,
        query,
        filters: AlertFilterParams,
        source_addr=None,
        target_addr=None,
        include_server_filter: bool = True,
    ):
        """
        Apply all filters to query.

        SINGLE SOURCE OF TRUTH for filter logic.
        No magic kwargs, explicit parameters only.

        Args:
            query: SQLAlchemy query to filter
            filters: Filter parameters
            source_addr: Address alias for source (defaults to self._source_addr)
            target_addr: Address alias for target (defaults to self._target_addr)
            include_server_filter: Whether to apply server filter (requires Node join)
        """
        # Use provided aliases or fall back to instance aliases
        source_addr = source_addr or self._source_addr
        target_addr = target_addr or self._target_addr

        # Date range filters
        if filters.start_date:
            # Future date check - return empty results
            if filters.start_date > get_current_time():
                return query.where(literal(False))
            query = query.where(DetectTime.time >= filters.start_date)

        if filters.end_date:
            query = query.where(DetectTime.time <= filters.end_date)

        # IP filters (exact match)
        if filters.source_ip:
            query = query.where(source_addr.address == filters.source_ip)

        if filters.target_ip:
            query = query.where(target_addr.address == filters.target_ip)

        # Severity filter (supports comma-separated)
        severity_list = filters.severity_list()
        if len(severity_list) == 1:
            query = query.where(Impact.severity == severity_list[0])
        elif len(severity_list) > 1:
            query = query.where(Impact.severity.in_(severity_list))

        # Classification filter (supports comma-separated)
        classification_list = filters.classification_list()
        if len(classification_list) == 1:
            query = query.where(Classification.text == classification_list[0])
        elif len(classification_list) > 1:
            query = query.where(Classification.text.in_(classification_list))

        # Server filter (Node.name prefix match) - optional, requires Node join
        if include_server_filter:
            server_list = filters.server_list()
            if len(server_list) == 1:
                query = query.where(Node.name.startswith(server_list[0] + "."))
            elif len(server_list) > 1:
                conditions = [Node.name.startswith(s + ".") for s in server_list]
                query = query.where(or_(*conditions))

        # Analyzer name filter
        if filters.analyzer_name:
            query = query.where(Analyzer.name == filters.analyzer_name)

        return query

    # =========================================================================
    # PUBLIC: Query Methods
    # =========================================================================

    def get_list(
        self,
        filters: AlertFilterParams,
        pagination: PaginationParams,
        sort_by: str = "detect_time",
        sort_order: str = "desc",
    ) -> tuple[list, int]:
        """
        Get paginated list of alerts with filters applied.

        Args:
            filters: Filter parameters
            pagination: Pagination parameters
            sort_by: Field to sort by
            sort_order: 'asc' or 'desc'

        Returns:
            Tuple of (results, total_count)
        """
        # Build query
        query = self._build_base_select()
        query = self._build_base_joins(query)
        query = self._apply_filters(query, filters)

        # Get total count before pagination
        total = self.count(query)

        # Apply sorting
        sort_column = self._get_sort_column(sort_by)
        if sort_column is not None:
            query = query.order_by(
                sort_column.desc() if sort_order == "desc" else sort_column.asc()
            )

        # Add stable secondary sort and apply pagination
        query = query.order_by(Alert._ident)
        results = self.paginate(query.distinct(), pagination.offset, pagination.size)

        return results, total

    def _get_sort_column(self, sort_by: str):
        """Map sort field name to SQLAlchemy column."""
        sort_map = {
            "detect_time": DetectTime.time,
            "create_time": CreateTime.time,
            "severity": Impact.severity,
            "classification": Classification.text,
            "source_ip": self._source_addr.address,
            "target_ip": self._target_addr.address,
            "analyzer": Analyzer.name,
            "alert_id": Alert._ident,
        }
        return sort_map.get(sort_by)

    def get_timeline(
        self,
        filters: AlertFilterParams,
        date_format: str,
    ) -> list:
        """
        Get timeline aggregation for chart display.

        Args:
            filters: Filter parameters
            date_format: MySQL DATE_FORMAT string for grouping

        Returns:
            List of aggregated timeline data points
        """
        source_addr = aliased(Address)
        target_addr = aliased(Address)

        query = (
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
            .outerjoin(Analyzer, get_analyzer_join_conditions(Alert._ident))
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
        )

        # Apply shared filter logic - pass local aliases, skip server filter (no Node join)
        query = self._apply_filters(
            query,
            filters,
            source_addr=source_addr,
            target_addr=target_addr,
            include_server_filter=False,  # Timeline query doesn't join Node
        )

        # Group and order
        query = query.group_by(
            text("time_bucket"), Impact.severity, Classification.text, Analyzer.name
        ).order_by(text("time_bucket"))

        return self.execute_all(query)

    def get_export_stream(
        self,
        filters: AlertFilterParams,
        alert_ids: list[int] | None = None,
        limit: int = 50000,
    ):
        """
        Get streaming query for CSV export.

        Args:
            filters: Filter parameters (ignored if alert_ids provided)
            alert_ids: Specific alert IDs to export (overrides filters)
            limit: Maximum number of results

        Returns:
            SQLAlchemy Result object configured for streaming (yield_per)
        """
        query = self._build_base_select()
        query = self._build_base_joins(query)

        # If specific alert IDs provided, filter by those only
        if alert_ids:
            query = query.where(Alert._ident.in_(alert_ids))
        else:
            # Apply standard filters
            query = self._apply_filters(query, filters)

        # Order by ID descending and limit
        query = query.order_by(Alert._ident.desc()).limit(limit)

        # Configure for streaming with server-side cursor
        query = query.execution_options(yield_per=1000)

        return self.db.execute(query)


# =========================================================================
# Dependency Injection - FastAPI pattern with proper Depends() chain
# =========================================================================


def get_alert_repository(
    db: Annotated[Session, Depends(get_prelude_db)],
) -> AlertRepository:
    """
    FastAPI dependency for AlertRepository.

    Usage in routes:
        from typing import Annotated

        @router.get("/alerts")
        async def list_alerts(
            repo: Annotated[AlertRepository, Depends(get_alert_repository)],
        ):
            return repo.get_list(...)
    """
    return AlertRepository(db)


def get_statistics_repository(
    db: Annotated[Session, Depends(get_prelude_db)],
) -> "StatisticsRepository":
    """FastAPI dependency for StatisticsRepository."""
    return StatisticsRepository(db)


def get_pair_table(request: Request) -> Table:
    """
    FastAPI dependency to get pair_table from app.state.

    Raises HTTPException 503 if table not available (reflected at startup).
    """
    pair_table = getattr(request.app.state, "pair_table", None)
    if pair_table is None:
        raise HTTPException(
            status_code=503,
            detail="Grouped alerts unavailable - Prebetter_Pair accelerator table not configured",
        )
    return pair_table


def get_grouped_alert_repository(
    db: Annotated[Session, Depends(get_prelude_db)],
    pair_table: Annotated[Table, Depends(get_pair_table)],
) -> "GroupedAlertRepository":
    """FastAPI dependency for GroupedAlertRepository."""
    return GroupedAlertRepository(db, pair_table)


def _filter_null_keys(results) -> dict:
    """Filter out null keys from query results. DRY helper for aggregations."""
    return {k: v for k, v in results if k}


class StatisticsRepository(BaseRepository):
    """
    Repository for statistics queries.

    Encapsulates all statistics aggregation logic.
    """

    def _base_alert_query(self, start_date, end_date):
        """Build base query with date filter applied. DRY helper."""
        return (
            select(Alert)
            .select_from(Alert)
            .join(DetectTime, Alert._ident == DetectTime._message_ident)
            .where(DetectTime.time >= start_date)
            .where(DetectTime.time <= end_date)
        )

    def _aggregation_query(self, select_cols, start_date, end_date):
        """Build aggregation query with date filter. DRY helper."""
        return (
            select(*select_cols)
            .select_from(Alert)
            .join(DetectTime, Alert._ident == DetectTime._message_ident)
            .where(DetectTime.time >= start_date)
            .where(DetectTime.time <= end_date)
        )

    def get_summary(self, start_date, end_date) -> dict:
        """
        Get aggregated statistics for alerts within time range.

        Args:
            start_date: Start of time range
            end_date: End of time range

        Returns:
            Dict with all aggregated statistics data
        """
        source_addr = aliased(Address)
        target_addr = aliased(Address)

        # Total alerts count
        base_subquery = self._base_alert_query(start_date, end_date).distinct().subquery()
        total_alerts = self.db.scalar(select(func.count()).select_from(base_subquery)) or 0

        # Severity distribution
        severity_query = (
            self._aggregation_query(
                [Impact.severity, func.count(Alert._ident.distinct())], start_date, end_date
            )
            .outerjoin(Impact, Impact._message_ident == Alert._ident)
            .group_by(Impact.severity)
        )
        alerts_by_severity = _filter_null_keys(self.db.execute(severity_query).all())

        # Classification distribution
        classification_query = (
            self._aggregation_query(
                [Classification.text, func.count(Alert._ident.distinct())], start_date, end_date
            )
            .outerjoin(Classification, Classification._message_ident == Alert._ident)
            .group_by(Classification.text)
        )
        alerts_by_classification = _filter_null_keys(self.db.execute(classification_query).all())

        # Analyzer distribution
        analyzer_query = (
            self._aggregation_query(
                [Analyzer.name, func.count(Alert._ident.distinct())], start_date, end_date
            )
            .outerjoin(Analyzer, get_analyzer_join_conditions(Alert._ident))
            .group_by(Analyzer.name)
        )
        alerts_by_analyzer = _filter_null_keys(self.db.execute(analyzer_query).all())

        # Top source IPs
        source_ip_query = (
            self._aggregation_query(
                [source_addr.address, func.count(Alert._ident.distinct())], start_date, end_date
            )
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
        alerts_by_source_ip = _filter_null_keys(self.db.execute(source_ip_query).all())

        # Top target IPs
        target_ip_query = (
            self._aggregation_query(
                [target_addr.address, func.count(Alert._ident.distinct())], start_date, end_date
            )
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
        alerts_by_target_ip = _filter_null_keys(self.db.execute(target_ip_query).all())

        return {
            "total_alerts": total_alerts,
            "alerts_by_severity": alerts_by_severity,
            "alerts_by_classification": alerts_by_classification,
            "alerts_by_analyzer": alerts_by_analyzer,
            "alerts_by_source_ip": alerts_by_source_ip,
            "alerts_by_target_ip": alerts_by_target_ip,
        }


class GroupedAlertRepository(BaseRepository):
    """
    Repository for grouped alerts (by source/target IP pair).

    Encapsulates all grouped query logic - no more 3 separate query builders.

    The pair_table is injected via DI from app.state (reflected once at startup).
    """

    def __init__(self, db: Session, pair_table: Table):
        super().__init__(db)
        self._pair_table = pair_table

    # =========================================================================
    # PRIVATE: Filter Helpers
    # =========================================================================

    def _apply_grouped_filters(self, query, filters: AlertFilterParams):
        """
        Apply filters optimized for grouped queries.

        Uses subquery pattern for better performance (semi-join optimization).
        """
        pair_table = self._pair_table

        # Date filters
        if filters.start_date:
            query = query.where(DetectTime.time >= ensure_timezone(filters.start_date))
        if filters.end_date:
            query = query.where(DetectTime.time <= ensure_timezone(filters.end_date))

        # IP filters (direct on pair table for performance)
        if filters.source_ip:
            query = query.where(pair_table.c.source_ip == func.inet_aton(filters.source_ip))
        if filters.target_ip:
            query = query.where(pair_table.c.target_ip == func.inet_aton(filters.target_ip))

        # Severity filter - use subquery to avoid Cartesian product
        if filters.severity:
            severity_list = filters.severity_list()
            if len(severity_list) == 1:
                severity_subq = select(Impact._message_ident).where(Impact.severity == severity_list[0])
            else:
                severity_subq = select(Impact._message_ident).where(Impact.severity.in_(severity_list))
            query = query.where(pair_table.c._message_ident.in_(severity_subq))

        # Classification filter - use subquery for semi-join optimization
        if filters.classification:
            classification_list = filters.classification_list()
            if len(classification_list) == 1:
                class_subq = select(Classification._message_ident).where(
                    Classification.text == classification_list[0]
                )
            else:
                class_subq = select(Classification._message_ident).where(
                    Classification.text.in_(classification_list)
                )
            query = query.where(pair_table.c._message_ident.in_(class_subq))

        # Server filter - uses subquery with Analyzer->Node join
        server_list = filters.server_list()
        if server_list:
            server_subq = (
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
            if len(server_list) == 1:
                server_subq = server_subq.where(Node.name.startswith(server_list[0] + "."))
            else:
                conditions = [Node.name.startswith(s + ".") for s in server_list]
                server_subq = server_subq.where(or_(*conditions))
            query = query.where(pair_table.c._message_ident.in_(server_subq))

        return query

    # =========================================================================
    # PUBLIC: Query Methods
    # =========================================================================

    def get_groups(
        self,
        filters: AlertFilterParams,
        pagination: PaginationParams,
        sort_by: str = "total_count",
        sort_order: str = "desc",
    ) -> dict:
        """
        Get paginated grouped alerts with all details.

        Args:
            filters: Filter parameters
            pagination: Pagination parameters
            sort_by: Field to sort by (detect_time, severity, classification, analyzer, source_ip, target_ip, total_count)
            sort_order: 'asc' or 'desc'

        Returns:
            Dict with groups, pagination info, and total alerts count
        """
        pair_table = self._pair_table

        # Determine which extra columns to include based on sort field
        sort_by_severity = sort_by == "severity"
        sort_by_classification = sort_by == "classification"
        sort_by_analyzer = sort_by == "analyzer"

        # =====================================================================
        # QUERY 1: Get paginated pairs with aggregations
        # =====================================================================
        select_cols = [
            func.inet_ntoa(pair_table.c.source_ip).label("source_ipv4"),
            func.inet_ntoa(pair_table.c.target_ip).label("target_ipv4"),
            func.max(DetectTime.time).label("latest_time"),
        ]

        pairs_query = (
            select(*select_cols)
            .select_from(DetectTime)
            .join(pair_table, pair_table.c._message_ident == DetectTime._message_ident)
        )

        # Apply filters
        pairs_query = self._apply_grouped_filters(pairs_query, filters)

        # Build sort columns mapping
        sort_cols = {
            "latest_time": literal_column("latest_time"),
            "source_ip": literal_column("source_ipv4"),
            "target_ip": literal_column("target_ipv4"),
            "max_severity": None,
            "max_classification": None,
            "max_analyzer": None,
        }

        classification_list = filters.classification_list()

        # Add severity column for sorting
        if sort_by_severity:
            pairs_query = pairs_query.add_columns(func.max(Impact.severity).label("max_severity"))
            pairs_query = pairs_query.outerjoin(
                Impact, Impact._message_ident == DetectTime._message_ident
            )
            sort_cols["max_severity"] = literal_column("max_severity")

        # Add classification column for sorting
        if sort_by_classification:
            pairs_query = pairs_query.add_columns(
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
            pairs_query = pairs_query.outerjoin(Classification, join_condition)
            sort_cols["max_classification"] = literal_column("max_classification")

        # Add analyzer column for sorting (using Node.name)
        if sort_by_analyzer:
            pairs_query = pairs_query.add_columns(func.max(Node.name).label("max_analyzer"))
            analyzer_join_condition = and_(
                Analyzer._message_ident == DetectTime._message_ident,
                Analyzer._parent_type == "A",
            )
            node_join_condition = and_(
                Node._message_ident == Analyzer._message_ident,
                Node._parent_type == "A",
                Node._parent0_index == Analyzer._index,
            )
            server_list = filters.server_list()
            if server_list:
                if len(server_list) == 1:
                    node_join_condition = and_(
                        node_join_condition, Node.name.startswith(server_list[0] + ".")
                    )
                else:
                    conditions = [Node.name.startswith(s + ".") for s in server_list]
                    node_join_condition = and_(node_join_condition, or_(*conditions))
            pairs_query = pairs_query.outerjoin(Analyzer, analyzer_join_condition)
            pairs_query = pairs_query.outerjoin(Node, node_join_condition)
            sort_cols["max_analyzer"] = literal_column("max_analyzer")

        # Add count column
        needs_distinct_count = sort_by_classification or sort_by_analyzer
        count_column = (
            func.count(func.distinct(pair_table.c._message_ident))
            if needs_distinct_count
            else func.count()
        )
        pairs_query = pairs_query.add_columns(count_column.label("total_count"))
        sort_cols["total_count"] = literal_column("total_count")

        # Group by pair key
        pairs_query = pairs_query.group_by(pair_table.c.pair_key)

        # =====================================================================
        # QUERY 2: Count total pairs for pagination
        # =====================================================================
        count_query = (
            select(func.count(func.distinct(pair_table.c.pair_key)))
            .select_from(DetectTime)
            .join(pair_table, pair_table.c._message_ident == DetectTime._message_ident)
        )
        count_query = self._apply_grouped_filters(count_query, filters)
        total_pairs = self.db.scalar(count_query) or 0

        # =====================================================================
        # Apply sorting and pagination to pairs query
        # =====================================================================
        sort_map = {
            "detect_time": sort_cols["latest_time"],
            "severity": sort_cols.get("max_severity"),
            "classification": sort_cols.get("max_classification"),
            "analyzer": sort_cols.get("max_analyzer"),
            "source_ip": sort_cols["source_ip"],
            "target_ip": sort_cols["target_ip"],
            "total_count": sort_cols["total_count"],
            "alert_id": sort_cols["total_count"],
        }
        order_col = sort_map.get(sort_by)
        if order_col is not None:
            pairs_query = pairs_query.order_by(
                order_col.desc() if sort_order == "desc" else order_col
            )

        # Execute paginated pairs query
        pairs = self.db.execute(
            pairs_query.offset(pagination.offset).limit(pagination.size)
        ).all()

        # =====================================================================
        # QUERY 3: Get details for the pairs on this page
        # =====================================================================
        if pairs:
            def ip_to_int(ip: str) -> int:
                return int(ipaddress.IPv4Address(ip))

            pair_keys = [
                (ip_to_int(p.source_ipv4) << 32) + ip_to_int(p.target_ipv4) for p in pairs
            ]

            detail_query = (
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
                .where(pair_table.c.pair_key.in_(pair_keys))
                .group_by(pair_table.c.pair_key, Classification.text)
            )

            # Apply filters to detail query
            if classification_list:
                if len(classification_list) == 1:
                    detail_query = detail_query.where(Classification.text == classification_list[0])
                else:
                    detail_query = detail_query.where(Classification.text.in_(classification_list))

            if filters.start_date:
                detail_query = detail_query.where(DetectTime.time >= ensure_timezone(filters.start_date))
            if filters.end_date:
                detail_query = detail_query.where(DetectTime.time <= ensure_timezone(filters.end_date))

            details = self.db.execute(detail_query).all()
        else:
            details = []

        # Return all data for route to process
        return {
            "pairs": pairs,
            "details": details,
            "total_pairs": total_pairs,
            "total_pages": pagination.total_pages(total_pairs),
        }
