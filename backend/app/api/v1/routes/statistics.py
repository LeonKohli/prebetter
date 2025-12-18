"""
Statistics routes using FastAPI best practices.

- Uses Repository pattern for data access
- Clean, explicit parameter handling
"""

import logging
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.datetime_utils import ensure_timezone, get_current_time, get_time_range
from app.repositories.alerts import (
    AlertRepository,
    StatisticsRepository,
    get_alert_repository,
    get_statistics_repository,
)
from app.schemas.filters import AlertFilterParams
from app.schemas.prelude import StatisticsSummary, TimelineDataPoint, TimelineResponse
from ..routes.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


class TimeFrame(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


DATE_FORMATS = {
    TimeFrame.HOUR: "%Y-%m-%d %H:00:00",
    TimeFrame.DAY: "%Y-%m-%d 00:00:00",
    TimeFrame.WEEK: "%Y-%m-%d 00:00:00",
    TimeFrame.MONTH: "%Y-%m-01 00:00:00",
}

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


def _aggregate_timeline_results(
    results, date_format: str, time_frame: TimeFrame
) -> list[TimelineDataPoint]:
    """Aggregate raw SQL results into TimelineDataPoint objects."""
    timeline_data: dict[datetime, dict] = {}

    for result in results:
        time_str = result.time_bucket
        if not time_str:
            continue

        timestamp = datetime.strptime(time_str, date_format).replace(tzinfo=UTC)

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
                data_point["by_classification"].get(result.classification, 0)
                + result.total
            )
        if result.analyzer:
            data_point["by_analyzer"][result.analyzer] = (
                data_point["by_analyzer"].get(result.analyzer, 0) + result.total
            )

    points = [TimelineDataPoint(**data) for data in timeline_data.values()]
    points.sort(key=lambda x: x.timestamp)
    return points


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    repo: Annotated[AlertRepository, Depends(get_alert_repository)],
    time_frame: TimeFrame = Query(TimeFrame.HOUR, description="Grouping interval"),
    start_date: datetime | None = Query(None, description="Start of date range (UTC)"),
    end_date: datetime | None = Query(None, description="End of date range (UTC)"),
    severity: str | None = Query(None, description="Filter by severity"),
    classification: str | None = Query(None, description="Filter by classification"),
    analyzer_name: str | None = Query(None, description="Filter by analyzer name"),
    source_ip: str | None = Query(
        None, description="Filter by source IP or CIDR (e.g., 192.168.0.0/16)"
    ),
    target_ip: str | None = Query(
        None, description="Filter by target IP or CIDR (e.g., 10.0.0.0/8)"
    ),
) -> TimelineResponse:
    """Get timeline data for alerts chart."""
    try:
        computed_start, computed_end = _compute_date_range(
            time_frame, start_date, end_date
        )

        filters = AlertFilterParams(
            start_date=computed_start,
            end_date=computed_end,
            severity=severity,
            classification=classification,
            analyzer_name=analyzer_name,
            source_ip=source_ip,
            target_ip=target_ip,
        )

        date_format = DATE_FORMATS[time_frame]
        results = repo.get_timeline(filters, date_format)
        timeline_points = _aggregate_timeline_results(results, date_format, time_frame)

        return TimelineResponse(
            time_frame=time_frame.value,
            start_date=computed_start,
            end_date=computed_end,
            data=timeline_points,
        )
    except Exception as e:
        logger.exception("Error generating timeline data: %s", e)
        raise HTTPException(status_code=500, detail="Error generating timeline data")


@router.get("/summary", response_model=StatisticsSummary)
async def get_statistics_summary(
    repo: Annotated[StatisticsRepository, Depends(get_statistics_repository)],
    time_range: int = Query(24, ge=1, le=720, description="Time range in hours"),
) -> StatisticsSummary:
    """Get summary statistics for alerts."""
    start_date, end_date = get_time_range(time_range)

    try:
        stats = repo.get_summary(start_date, end_date)
        return StatisticsSummary(
            total_alerts=stats["total_alerts"],
            alerts_by_severity=stats["alerts_by_severity"],
            alerts_by_classification=stats["alerts_by_classification"],
            alerts_by_analyzer=stats["alerts_by_analyzer"],
            alerts_by_source_ip=stats["alerts_by_source_ip"],
            alerts_by_target_ip=stats["alerts_by_target_ip"],
            time_range_hours=time_range,
            start_at=start_date,
            end_at=end_date,
        )
    except Exception as e:
        logger.exception("Error generating statistics summary: %s", e)
        raise HTTPException(
            status_code=500, detail="Error generating statistics summary"
        )
