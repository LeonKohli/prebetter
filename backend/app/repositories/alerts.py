"""
Alert Repository - Data access layer for alerts.

Encapsulates ALL alert query logic. Routes never touch SQLAlchemy directly.
Filter logic lives in ONE place - no more scattered apply_* functions.

Usage:
    repo = AlertRepository(db)
    alerts = repo.get_list(filters, pagination)
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session, aliased
from sqlalchemy import select, func, and_, literal_column, literal, or_, text

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
from app.database.config import get_analyzer_join_conditions, get_node_join_conditions
from app.core.datetime_utils import get_current_time


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

    def _apply_filters(self, query, filters: AlertFilterParams):
        """
        Apply all filters to query.

        SINGLE SOURCE OF TRUTH for filter logic.
        No magic kwargs, explicit parameters only.
        """
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
            query = query.where(self._source_addr.address == filters.source_ip)

        if filters.target_ip:
            query = query.where(self._target_addr.address == filters.target_ip)

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

        # Server filter (Node.name prefix match)
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

        # Apply filters directly (not using _apply_filters because different aliases)
        if filters.start_date:
            query = query.where(DetectTime.time >= filters.start_date)
        if filters.end_date:
            query = query.where(DetectTime.time <= filters.end_date)
        if filters.severity:
            query = query.where(Impact.severity == filters.severity)
        if filters.classification:
            query = query.where(Classification.text == filters.classification)
        if filters.analyzer_name:
            query = query.where(Analyzer.name == filters.analyzer_name)
        if filters.source_ip:
            query = query.where(source_addr.address == filters.source_ip)
        if filters.target_ip:
            query = query.where(target_addr.address == filters.target_ip)

        # Group and order
        query = query.group_by(
            text("time_bucket"), Impact.severity, Classification.text, Analyzer.name
        ).order_by(text("time_bucket"))

        return self.execute_all(query)


# =========================================================================
# Dependency Injection
# =========================================================================


def get_alert_repository(db: Session) -> AlertRepository:
    """
    FastAPI dependency for AlertRepository.

    Usage in routes:
        @router.get("/alerts")
        async def list_alerts(
            repo: AlertRepository = Depends(get_alert_repository),
        ):
    """
    return AlertRepository(db)
