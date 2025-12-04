from sqlalchemy import create_engine, MetaData, and_, literal, func, event
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from typing import Generator, Optional
from datetime import datetime
from ..core.config import get_settings
from ..core.datetime_utils import get_current_time, ensure_timezone

settings = get_settings()

# Create SQLAlchemy engines for both databases
# Using SQLAlchemy 2.0 best practices with future=True for forward compatibility
prelude_engine = create_engine(
    settings.PRELUDE_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    echo=False,  # SQL logging disabled - too noisy even in debug
    future=True,  # Enable 2.0 style behaviors
)

prebetter_engine = create_engine(
    settings.PREBETTER_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    echo=False,  # SQL logging disabled - too noisy even in debug
    future=True,  # Enable 2.0 style behaviors
)


# Force UTC timezone on every connection using SQLAlchemy events
@event.listens_for(prelude_engine, "connect")
def set_prelude_timezone(dbapi_conn, connection_record):
    """Set MySQL session timezone to UTC for all connections."""
    cursor = dbapi_conn.cursor()
    cursor.execute("SET time_zone='+00:00'")
    cursor.close()


@event.listens_for(prebetter_engine, "connect")
def set_prebetter_timezone(dbapi_conn, connection_record):
    """Set MySQL session timezone to UTC for all connections."""
    cursor = dbapi_conn.cursor()
    cursor.execute("SET time_zone='+00:00'")
    cursor.close()


# Create metadata objects
prelude_metadata = MetaData()

prebetter_metadata = MetaData()

# Create session factories with SQLAlchemy 2.0 configuration
# autocommit=False is the default in 2.0, explicitly set for clarity
# expire_on_commit=False can improve performance in read-heavy scenarios
PreludeSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=prelude_engine,
    expire_on_commit=False,  # Prevents unnecessary refreshes for read-only data
    future=True,  # Enable 2.0 style session behaviors
)
PrebetterSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=prebetter_engine,
    future=True,  # Enable 2.0 style session behaviors
)


# Create base classes for declarative models using v2 syntax
class PreludeBase(DeclarativeBase):
    metadata = prelude_metadata


class PrebetterBase(DeclarativeBase):
    metadata = prebetter_metadata


def get_prelude_db() -> Generator[Session, None, None]:
    db = PreludeSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_prebetter_db() -> Generator[Session, None, None]:
    db = PrebetterSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Common query helpers to reduce duplicated code


def apply_standard_alert_filters(
    query,
    severity: Optional[str] = None,
    classification: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    source_ip: Optional[str] = None,
    target_ip: Optional[str] = None,
    server: Optional[str] = None,
    **models,
):
    """
    Apply standard alert filters to a query in a more optimized way.

    Args:
        query: The SQLAlchemy query to filter
        severity: Optional severity filter
        classification: Optional classification filter (partial match)
        start_date: Optional start date filter
        end_date: Optional end date filter
        source_ip: Optional source IP filter (exact match)
        target_ip: Optional target IP filter (exact match)
        server: Optional server name filter (short node name like server-001)
        models: Dict containing model classes. Expected keys: Impact, Classification,
                DetectTime, source_addr, target_addr, Node

    Returns:
        Filtered SQLAlchemy query
    """
    Impact = models.get("Impact")
    Classification = models.get("Classification")
    DetectTime = models.get("DetectTime")
    source_addr = models.get("source_addr")
    target_addr = models.get("target_addr")
    # Optional integer IP columns when using Prebetter_Pair
    source_ip_int_col = models.get("source_ip_int_col")
    target_ip_int_col = models.get("target_ip_int_col")

    # Apply filters progressively from most to least selective for better query planning

    # Apply date range filters with proper timezone handling
    if start_date and DetectTime:
        # Ensure timezone consistency using utility
        start_date = ensure_timezone(start_date)
        query = query.where(DetectTime.time >= start_date)

    if end_date and DetectTime:
        # Ensure timezone consistency using utility
        end_date = ensure_timezone(end_date)
        query = query.where(DetectTime.time <= end_date)

    # Check for future date range (edge case handling)
    current_time = get_current_time()  # Using utility function
    if start_date and start_date > current_time:
        # If the start date is in the future, ensure empty results
        # This is needed for test_list_alerts_edge_cases
        query = query.where(literal(False))

    # Apply exact match filters first (likely most selective)
    if source_ip:
        if source_ip_int_col is not None:
            query = query.where(source_ip_int_col == func.inet_aton(source_ip))
        elif source_addr:
            # Using exact equality without func.binary() for better index utilization
            query = query.where(source_addr.address == source_ip)

    if target_ip:
        if target_ip_int_col is not None:
            query = query.where(target_ip_int_col == func.inet_aton(target_ip))
        elif target_addr:
            # Using exact equality without func.binary() for better index utilization
            query = query.where(target_addr.address == target_ip)

    if severity and Impact:
        severity_list = [s.strip() for s in severity.split(",") if s.strip()]
        if len(severity_list) == 1:
            query = query.where(Impact.severity == severity_list[0])
        elif len(severity_list) > 1:
            query = query.where(Impact.severity.in_(severity_list))

    # Filter by server (Node.name) - matches short node name like server-001
    Node = models.get("Node")
    if server and Node:
        server_list = [s.strip() for s in server.split(",") if s.strip()]
        # Filter by short node name - match beginning of FQDN
        if len(server_list) == 1:
            query = query.where(Node.name.startswith(server_list[0] + "."))
        elif len(server_list) > 1:
            # For multiple values, use OR conditions
            from sqlalchemy import or_

            conditions = [Node.name.startswith(s + ".") for s in server_list]
            query = query.where(or_(*conditions))

    if classification and Classification:
        classification_list = [c.strip() for c in classification.split(",") if c.strip()]
        if len(classification_list) == 1:
            query = query.where(Classification.text == classification_list[0])
        elif len(classification_list) > 1:
            query = query.where(Classification.text.in_(classification_list))

    return query


def get_analyzer_join_conditions(message_ident_field, parent_type="A", index=-1):
    """
    Get standard analyzer join conditions.

    Args:
        message_ident_field: The field to join on (_message_ident)
        parent_type: The parent type to filter on (default "A")
        index: The index to filter on (default -1)

    Returns:
        SQLAlchemy join conditions
    """
    from ..models.prelude import Analyzer

    return and_(
        Analyzer._message_ident == message_ident_field,
        Analyzer._parent_type == parent_type,
        Analyzer._index == index,
    )


def get_source_address_join_conditions(
    message_ident_field, parent_index=-1, category="ipv4-addr"
):
    """Get standard source address join conditions"""
    from ..models.prelude import Address

    return and_(
        Address._message_ident == message_ident_field,
        Address._parent_type == "S",
        Address._parent0_index == parent_index,
        Address.category == category,
    )


def get_target_address_join_conditions(
    message_ident_field, parent_index=-1, category="ipv4-addr"
):
    """Get standard target address join conditions"""
    from ..models.prelude import Address

    return and_(
        Address._message_ident == message_ident_field,
        Address._parent_type == "T",
        Address._parent0_index == parent_index,
        Address.category == category,
    )


def get_node_join_conditions(message_ident_field, parent_type="A", parent0_index=-1):
    """Get standard node join conditions"""
    from ..models.prelude import Node

    return and_(
        Node._message_ident == message_ident_field,
        Node._parent_type == parent_type,
        Node._parent0_index == parent0_index,
    )


def apply_sorting(query, sort_by, sort_order, sort_options, default_column=None):
    """
    Apply sorting to a query based on the field and order.

    Args:
        query: The SQLAlchemy query to sort
        sort_by: The field to sort by (string or enum value)
        sort_order: The order to sort ("asc"/"desc" or ASC/DESC enum value)
        sort_options: Dict mapping field names to column objects
        default_column: Default column to sort by if sort_by not in options

    Returns:
        Sorted SQLAlchemy query
    """
    # Convert sort_by to string if it's an enum
    sort_key = sort_by
    if hasattr(sort_by, "value"):
        sort_key = sort_by.value

    # Get the sort column from options, or use default
    sort_column = sort_options.get(sort_key)
    if not sort_column and default_column:
        sort_column = default_column

    if not sort_column:
        return query

    # Apply sorting direction
    if hasattr(sort_order, "value"):
        # Handle enum values
        sort_order = sort_order.value

    if str(sort_order).lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    return query
