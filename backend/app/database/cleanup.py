from datetime import timedelta
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.prelude import Heartbeat, AnalyzerTime
from app.core.datetime_utils import get_current_time


def cleanup_old_heartbeats(
    db: Session, retention_days: int = 30, dry_run: bool = False
) -> tuple[int, int]:
    cutoff_time = get_current_time() - timedelta(days=retention_days)

    old_heartbeats_query = (
        select(Heartbeat._ident)
        .join(
            AnalyzerTime,
            and_(
                AnalyzerTime._message_ident == Heartbeat._ident,
                AnalyzerTime._parent_type == "H",
            ),
        )
        .group_by(Heartbeat._ident)
        .having(func.max(AnalyzerTime.time) < cutoff_time)
    )

    orphaned_heartbeats_query = (
        select(Heartbeat._ident)
        .outerjoin(
            AnalyzerTime,
            and_(
                AnalyzerTime._message_ident == Heartbeat._ident,
                AnalyzerTime._parent_type == "H",
            ),
        )
        .group_by(Heartbeat._ident)
        .having(func.count(AnalyzerTime._message_ident) == 0)
    )

    old_heartbeat_ids_with_time = [row[0] for row in db.execute(old_heartbeats_query)]
    orphaned_heartbeat_ids = [row[0] for row in db.execute(orphaned_heartbeats_query)]

    all_heartbeat_ids = list(set(old_heartbeat_ids_with_time + orphaned_heartbeat_ids))

    if not all_heartbeat_ids:
        return 0, 0

    if dry_run:
        analyzer_times_count = (
            db.query(AnalyzerTime)
            .filter(
                and_(
                    AnalyzerTime._message_ident.in_(all_heartbeat_ids),
                    AnalyzerTime._parent_type == "H",
                )
            )
            .count()
        )

        heartbeats_count = len(all_heartbeat_ids)

        return heartbeats_count, analyzer_times_count

    deleted_analyzer_times = (
        db.query(AnalyzerTime)
        .filter(
            and_(
                AnalyzerTime._message_ident.in_(all_heartbeat_ids),
                AnalyzerTime._parent_type == "H",
            )
        )
        .delete(synchronize_session=False)
    )

    deleted_heartbeats = (
        db.query(Heartbeat)
        .filter(Heartbeat._ident.in_(all_heartbeat_ids))
        .delete(synchronize_session=False)
    )

    db.commit()

    return deleted_heartbeats, deleted_analyzer_times


def cleanup_orphaned_analyzer_times(db: Session, dry_run: bool = False) -> int:
    existing_heartbeats = select(Heartbeat._ident)

    if dry_run:
        orphaned_count = (
            db.query(AnalyzerTime)
            .filter(
                and_(
                    AnalyzerTime._parent_type == "H",
                    ~AnalyzerTime._message_ident.in_(existing_heartbeats),
                )
            )
            .count()
        )
        return orphaned_count

    deleted_count = (
        db.query(AnalyzerTime)
        .filter(
            and_(
                AnalyzerTime._parent_type == "H",
                ~AnalyzerTime._message_ident.in_(existing_heartbeats),
            )
        )
        .delete(synchronize_session=False)
    )

    db.commit()

    return deleted_count
