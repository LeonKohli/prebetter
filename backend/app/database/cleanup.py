from datetime import timedelta
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.prelude import Heartbeat, AnalyzerTime
from app.core.datetime_utils import get_current_time

def cleanup_old_heartbeats(db: Session, retention_days: int = 30) -> tuple[int, int]:
    """
    Clean up old heartbeats and related data that are older than the retention period.
    
    This function:
    1. Identifies heartbeats older than retention_days
    2. Deletes related analyzer time entries
    3. Deletes the old heartbeats
    4. Returns the number of deleted records
    
    Args:
        db: SQLAlchemy database session
        retention_days: Number of days to keep heartbeats (default: 30)
        
    Returns:
        Tuple of (deleted_heartbeats_count, deleted_analyzer_times_count)
    """
    cutoff_time = get_current_time() - timedelta(days=retention_days)
    
    # First, identify heartbeats to delete:
    # 1. Heartbeats with analyzer times older than cutoff_time
    # 2. Heartbeats without any analyzer times (these are considered orphaned)
    
    # Find heartbeats with analyzer times older than the cutoff
    old_heartbeats_query = (
        select(Heartbeat._ident)
        .join(
            AnalyzerTime,
            and_(
                AnalyzerTime._message_ident == Heartbeat._ident,
                AnalyzerTime._parent_type == "H"
            )
        )
        .group_by(Heartbeat._ident)
        .having(func.max(AnalyzerTime.time) < cutoff_time)
    )
    
    # Find heartbeats without analyzer times
    orphaned_heartbeats_query = (
        select(Heartbeat._ident)
        .outerjoin(
            AnalyzerTime,
            and_(
                AnalyzerTime._message_ident == Heartbeat._ident,
                AnalyzerTime._parent_type == "H"
            )
        )
        .group_by(Heartbeat._ident)
        .having(func.count(AnalyzerTime._message_ident) == 0)
    )
    
    # Combine the IDs from both queries
    old_heartbeat_ids_with_time = [row[0] for row in db.execute(old_heartbeats_query)]
    orphaned_heartbeat_ids = [row[0] for row in db.execute(orphaned_heartbeats_query)]
    
    # Combine all heartbeat IDs to delete
    all_heartbeat_ids = list(set(old_heartbeat_ids_with_time + orphaned_heartbeat_ids))
    
    if not all_heartbeat_ids:
        return 0, 0
    
    # Delete analyzer times for old heartbeats
    deleted_analyzer_times = (
        db.query(AnalyzerTime)
        .filter(
            and_(
                AnalyzerTime._message_ident.in_(all_heartbeat_ids),
                AnalyzerTime._parent_type == "H"
            )
        )
        .delete(synchronize_session=False)
    )
    
    # Delete old heartbeats
    deleted_heartbeats = (
        db.query(Heartbeat)
        .filter(Heartbeat._ident.in_(all_heartbeat_ids))
        .delete(synchronize_session=False)
    )
    
    # Commit the changes
    db.commit()
    
    return deleted_heartbeats, deleted_analyzer_times

def cleanup_orphaned_analyzer_times(db: Session) -> int:
    """
    Clean up orphaned analyzer time entries that don't have corresponding heartbeats.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        Number of deleted orphaned records
    """
    # Find heartbeat IDs that exist
    existing_heartbeats = select(Heartbeat._ident)
    
    # Delete analyzer times that don't have corresponding heartbeats
    deleted_count = (
        db.query(AnalyzerTime)
        .filter(
            and_(
                AnalyzerTime._parent_type == "H",
                ~AnalyzerTime._message_ident.in_(existing_heartbeats)
            )
        )
        .delete(synchronize_session=False)
    )
    
    # Commit the changes
    db.commit()
    
    return deleted_count 