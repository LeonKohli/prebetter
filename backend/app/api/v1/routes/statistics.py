"""
Statistics routes using FastAPI best practices.

- Uses Pydantic filter schemas as dependencies
- Uses Repository pattern for data access
- Clean, explicit parameter handling
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session
from enum import Enum

from app.database.config import get_prelude_db
from app.database.query_builders import build_alerts_statistics_query
from app.repositories.alerts import AlertRepository
from app.schemas.filters import AlertFilterParams
from app.schemas.prelude import TimelineResponse, TimelineDataPoint, StatisticsSummary
from app.core.datetime_utils import get_current_time, ensure_timezone, get_time_range
from ..routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


class TimeFrame(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


# Date format strings for MySQL DATE_FORMAT
DATE_FORMATS = {
    TimeFrame.HOUR: "%Y-%m-%d %H:00:00",
    TimeFrame.DAY: "%Y-%m-%d 00:00:00",
    TimeFrame.WEEK: "%Y-%m-%d 00:00:00",
    TimeFrame.MONTH: "%Y-%m-01 00:00:00",
}

# Default date ranges per time frame
DEFAULT_RANGES = {
    TimeFrame.HOUR: timedelta(days=1),
    TimeFrame.DAY: timedelta(days=30),
    TimeFrame.WEEK: timedelta(days=90),
    TimeFrame.MONTH: timedelta(days=365),
}


def _compute_date_range(
    time_frame: TimeFrame,
    start_date: datetime | None,
    end_date: datetime | None,
) -> tuple[datetime, datetime]:
    """Compute date range with defaults based on time frame."""
    if not end_date:
        end_date = get_current_time()
    if not start_date:
        start_date = end_date - DEFAULT_RANGES[time_frame]

    return ensure_timezone(start_date), ensure_timezone(end_date)


def _aggregate_timeline_results(results, date_format: str, time_frame: TimeFrame) -> list[TimelineDataPoint]:
    """
    Aggregate raw SQL results into TimelineDataPoint objects.

    Groups by timestamp and aggregates counts per severity/classification/analyzer.
    """
    timeline_data: dict[datetime, dict] = {}

    for result in results:
        time_str = result.time_bucket
        if not time_str:
            continue

        timestamp = datetime.strptime(time_str, date_format).replace(tzinfo=UTC)

        # Align to week start for weekly grouping
        if time_frame == TimeFrame.WEEK:
            timestamp = timestamp - timedelta(days=timestamp.weekday())

        if timestamp not in timeline_data:
            timeline_data[timestamp] = {
                "timestamp": timestamp,
                "total": 0,
                "by_severity": {},
                "by_classification": {},
                "by_analyzer": {},
            }

        data_point = timeline_data[timestamp]
        data_point["total"] += result.total

        if result.severity:
            data_point["by_severity"][result.severity] = (
                data_point["by_severity"].get(result.severity, 0) + result.total
            )

        if result.classification:
            data_point["by_classification"][result.classification] = (
                data_point["by_classification"].get(result.classification, 0) + result.total
            )

        if result.analyzer:
            data_point["by_analyzer"][result.analyzer] = (
                data_point["by_analyzer"].get(result.analyzer, 0) + result.total
            )

    # Sort by timestamp and convert to Pydantic models
    points = [TimelineDataPoint(**data) for data in timeline_data.values()]
    points.sort(key=lambda x: x.timestamp)
    return points


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    time_frame: TimeFrame = Query(TimeFrame.HOUR, description="Grouping interval"),
    # Filter params - using explicit Query for OpenAPI docs
    start_date: datetime | None = Query(None, description="Start of date range (UTC)"),
    end_date: datetime | None = Query(None, description="End of date range (UTC)"),
    severity: str | None = Query(None, description="Filter by severity"),
    classification: str | None = Query(None, description="Filter by classification"),
    analyzer_name: str | None = Query(None, description="Filter by analyzer name"),
    source_ip: str | None = Query(None, description="Filter by source IP"),
    target_ip: str | None = Query(None, description="Filter by target IP"),
    db: Session = Depends(get_prelude_db),
) -> TimelineResponse:
    """
    Get timeline data for alerts chart.

    Supports filtering by all standard alert filters.
    Groups alerts into time buckets based on time_frame.
    """
    try:
        # Compute date range with defaults
        computed_start, computed_end = _compute_date_range(time_frame, start_date, end_date)

        # Build filter params object
        filters = AlertFilterParams(
            start_date=computed_start,
            end_date=computed_end,
            severity=severity,
            classification=classification,
            analyzer_name=analyzer_name,
            source_ip=source_ip,
            target_ip=target_ip,
        )

        # Use repository for data access
        repo = AlertRepository(db)
        date_format = DATE_FORMATS[time_frame]
        results = repo.get_timeline(filters, date_format)

        # Aggregate results
        timeline_points = _aggregate_timeline_results(results, date_format, time_frame)

        return TimelineResponse(
            time_frame=time_frame.value,
            start_date=computed_start,
            end_date=computed_end,
            data=timeline_points,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Error generating timeline data")


@router.get("/summary", response_model=StatisticsSummary)
async def get_statistics_summary(
    time_range: int = Query(24, ge=1, le=720, description="Time range in hours to analyze"),
    db: Session = Depends(get_prelude_db),
) -> StatisticsSummary:
    """
    Get summary statistics for alerts.

    Returns counts grouped by severity, classification, analyzer, and IPs.
    """
    start_date, end_date = get_time_range(time_range)
    query = build_alerts_statistics_query(db, start_date, end_date)

    try:
        from sqlalchemy import func, select

        # Count total alerts
        base_subquery = query["base"].distinct().subquery()
        total_alerts = db.scalar(select(func.count()).select_from(base_subquery)) or 0

        # Execute all distribution queries
        alerts_by_severity = db.execute(query["severity"]).all()
        alerts_by_classification = db.execute(query["classification"]).all()
        alerts_by_analyzer = db.execute(query["analyzer"]).all()
        alerts_by_source_ip = db.execute(query["source_ip"]).all()
        alerts_by_target_ip = db.execute(query["target_ip"]).all()

        return StatisticsSummary(
            total_alerts=total_alerts,
            alerts_by_severity={k: v for k, v in alerts_by_severity if k},
            alerts_by_classification={k: v for k, v in alerts_by_classification if k},
            alerts_by_analyzer={k: v for k, v in alerts_by_analyzer if k},
            alerts_by_source_ip={k: v for k, v in alerts_by_source_ip if k},
            alerts_by_target_ip={k: v for k, v in alerts_by_target_ip if k},
            time_range_hours=time_range,
            start_at=start_date,
            end_at=end_date,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Error generating statistics summary")
