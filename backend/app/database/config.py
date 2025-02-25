from sqlalchemy import create_engine, MetaData, and_, func
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator, Optional, Dict, Any
from datetime import datetime
from ..core.config import get_settings

settings = get_settings()

# Create SQLAlchemy engines for both databases
prelude_engine = create_engine(
    settings.PRELUDE_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)

prebetter_engine = create_engine(
    settings.PREBETTER_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)

# Create metadata objects
prelude_metadata = MetaData()
prelude_metadata.bind = prelude_engine

prebetter_metadata = MetaData()
prebetter_metadata.bind = prebetter_engine

# Create session factories
PreludeSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=prelude_engine)
PrebetterSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=prebetter_engine)

# Create base classes for declarative models
PreludeBase = declarative_base(metadata=prelude_metadata)
PrebetterBase = declarative_base(metadata=prebetter_metadata)

def get_prelude_db() -> Generator[Session, None, None]:
    """Dependency for getting prelude database session"""
    db = PreludeSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_prebetter_db() -> Generator[Session, None, None]:
    """Dependency for getting prebetter database session"""
    db = PrebetterSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Common query helpers to reduce duplicated code

def apply_standard_alert_filters(query, 
                               severity: Optional[str] = None,
                               classification: Optional[str] = None,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               source_ip: Optional[str] = None,
                               target_ip: Optional[str] = None,
                               analyzer_model: Optional[str] = None,
                               **models):
    """
    Apply standard alert filters to a query.
    
    Args:
        query: The SQLAlchemy query to filter
        severity: Optional severity filter
        classification: Optional classification filter (partial match)
        start_date: Optional start date filter
        end_date: Optional end date filter
        source_ip: Optional source IP filter (exact match)
        target_ip: Optional target IP filter (exact match)
        analyzer_model: Optional analyzer model filter
        models: Dict containing model classes. Expected keys: Impact, Classification, 
                DetectTime, source_addr, target_addr, Analyzer
    
    Returns:
        Filtered SQLAlchemy query
    """
    Impact = models.get('Impact')
    Classification = models.get('Classification')
    DetectTime = models.get('DetectTime')
    source_addr = models.get('source_addr')
    target_addr = models.get('target_addr')
    Analyzer = models.get('Analyzer')
    
    if severity and Impact:
        query = query.filter(Impact.severity == severity)
    if classification and Classification:
        query = query.filter(Classification.text.like(f"%{classification}%"))
    if start_date and DetectTime:
        query = query.filter(DetectTime.time >= start_date)
    if end_date and DetectTime:
        query = query.filter(DetectTime.time <= end_date)
    if source_ip and source_addr:
        query = query.filter(func.binary(source_addr.address) == source_ip)
    if target_ip and target_addr:
        query = query.filter(func.binary(target_addr.address) == target_ip)
    if analyzer_model and Analyzer:
        query = query.filter(Analyzer.model == analyzer_model)
    
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

def get_source_address_join_conditions(message_ident_field, parent_index=-1, category="ipv4-addr"):
    """Get standard source address join conditions"""
    from ..models.prelude import Address
    
    return and_(
        Address._message_ident == message_ident_field,
        Address._parent_type == "S",
        Address._parent0_index == parent_index,
        Address.category == category,
    )

def get_target_address_join_conditions(message_ident_field, parent_index=-1, category="ipv4-addr"):
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
    # Get the sort column from options, or use default
    sort_column = sort_options.get(str(sort_by))
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
