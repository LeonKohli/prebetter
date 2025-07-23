from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database.config import get_prelude_db, apply_standard_alert_filters
from app.database.query_builders import (
    build_alerts_timeline_query,
    build_alerts_statistics_query,
)
from app.models.prelude import DetectTime, Impact, Classification, Analyzer
from app.schemas.prelude import TimelineResponse, TimelineDataPoint, StatisticsSummary
from app.core.datetime_utils import get_current_time, ensure_timezone, get_time_range
from enum import Enum
from ..routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


class GroupBy(str, Enum):
    SEVERITY = "severity"
    CLASSIFICATION = "classification"
    ANALYZER = "analyzer"
    SOURCE = "source"
    TARGET = "target"


class TimeFrame(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    time_frame: TimeFrame = Query(TimeFrame.HOUR, description="Grouping interval"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    severity: Optional[str] = None,
    classification: Optional[str] = None,
    analyzer_name: Optional[str] = None,
    db: Session = Depends(get_prelude_db),
) -> TimelineResponse:
    try:
        if not end_date:
            end_date = get_current_time()
        if not start_date:
            if time_frame == TimeFrame.HOUR:
                start_date = end_date - timedelta(days=1)
            elif time_frame == TimeFrame.DAY:
                start_date = end_date - timedelta(days=30)
            elif time_frame == TimeFrame.WEEK:
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=365)

        start_date = ensure_timezone(start_date)
        end_date = ensure_timezone(end_date)
        if time_frame == TimeFrame.HOUR:
            date_format = "%Y-%m-%d %H:00:00"
        elif time_frame == TimeFrame.DAY:
            date_format = "%Y-%m-%d 00:00:00"
        elif time_frame == TimeFrame.WEEK:
            date_format = "%Y-%m-%d 00:00:00"
        else:
            date_format = "%Y-%m-01 00:00:00"

        timeline_query = build_alerts_timeline_query(db, date_format)

        timeline_query = timeline_query.filter(DetectTime.time >= start_date)
        timeline_query = timeline_query.filter(DetectTime.time <= end_date)

        timeline_query = apply_standard_alert_filters(
            query=timeline_query,
            severity=severity,
            classification=classification,
            analyzer_model=None,
            Impact=Impact,
            Classification=Classification,
            DetectTime=DetectTime,
        )

        if analyzer_name:
            timeline_query = timeline_query.filter(Analyzer.name == analyzer_name)

        results = (
            timeline_query.group_by(
                text("time_bucket"), Impact.severity, Classification.text, Analyzer.name
            )
            .order_by(text("time_bucket"))
            .all()
        )

        timeline_data = {}
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

        timeline_points = [TimelineDataPoint(**data) for data in timeline_data.values()]
        timeline_points.sort(key=lambda x: x.timestamp)

        return TimelineResponse(
            time_frame=time_frame,
            start_date=start_date or get_current_time(),
            end_date=end_date or get_current_time(),
            data=timeline_points,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating timeline data: {str(e)}"
        )


@router.get("/summary", response_model=StatisticsSummary)
async def get_statistics_summary(
    time_range: int = Query(
        24, ge=1, le=720, description="Time range in hours to analyze"
    ),
    db: Session = Depends(get_prelude_db),
) -> StatisticsSummary:
    start_date, end_date = get_time_range(time_range)

    query = build_alerts_statistics_query(db, start_date, end_date)

    try:
        total_alerts = query["base"].distinct().count()

        alerts_by_severity = query["severity"].all()
        severity_distribution = {
            severity: count for severity, count in alerts_by_severity if severity
        }

        alerts_by_classification = query["classification"].all()
        classification_distribution = {
            classification: count
            for classification, count in alerts_by_classification
            if classification
        }

        alerts_by_analyzer = query["analyzer"].all()
        analyzer_distribution = {
            analyzer: count for analyzer, count in alerts_by_analyzer if analyzer
        }

        alerts_by_source_ip = query["source_ip"].all()
        source_ip_distribution = {ip: count for ip, count in alerts_by_source_ip if ip}

        alerts_by_target_ip = query["target_ip"].all()
        target_ip_distribution = {ip: count for ip, count in alerts_by_target_ip if ip}

        return StatisticsSummary(
            total_alerts=total_alerts,
            alerts_by_severity=severity_distribution,
            alerts_by_classification=classification_distribution,
            alerts_by_analyzer=analyzer_distribution,
            alerts_by_source_ip=source_ip_distribution,
            alerts_by_target_ip=target_ip_distribution,
            time_range_hours=time_range,
            start_at=start_date,
            end_at=end_date,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating statistics summary: {str(e)}"
        )
