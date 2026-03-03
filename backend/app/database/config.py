from sqlalchemy import create_engine, MetaData, and_, event
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from collections.abc import Generator
from ..core.config import get_settings

settings = get_settings()

# Create SQLAlchemy engines for both databases
prelude_engine = create_engine(
    settings.PRELUDE_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    connect_args={"connect_timeout": 10, "read_timeout": 30, "write_timeout": 30},
    echo=False,
)

prebetter_engine = create_engine(
    settings.PREBETTER_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    connect_args={"connect_timeout": 10, "read_timeout": 30, "write_timeout": 30},
    echo=False,
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

# Create session factories
# expire_on_commit=False prevents unnecessary refreshes for read-only data
PreludeSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=prelude_engine,
    expire_on_commit=False,
)
PrebetterSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=prebetter_engine,
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
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_prebetter_db() -> Generator[Session, None, None]:
    db = PrebetterSessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Common query helpers - join conditions


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
