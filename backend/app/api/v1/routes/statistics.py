from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_, text
from app.database.config import get_prelude_db
from app.models.prelude import Alert, DetectTime, Impact, Classification, Analyzer, Address
from app.schemas.prelude import TimelineResponse, TimelineDataPoint, StatisticsSummary
from enum import Enum
from fastapi import HTTPException
from app.api.v1.routes.auth import get_current_user
from app.core.datetime_utils import ensure_timezone, get_current_time, get_time_range

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
    """
    Get alert timeline data grouped by the specified time frame.
    Supports filtering by severity, classification, and analyzer.
    """
    try:
        # Set default time range if not provided and ensure timezone awareness
        if not end_date:
            end_date = get_current_time()
        else:
            end_date = ensure_timezone(end_date)

        if not start_date:
            if time_frame == TimeFrame.HOUR:
                start_date = end_date - timedelta(hours=24)
            elif time_frame == TimeFrame.DAY:
                start_date = end_date - timedelta(days=30)
            elif time_frame == TimeFrame.WEEK:
                start_date = end_date - timedelta(weeks=12)
            else:  # month
                start_date = end_date - timedelta(days=365)
        else:
            start_date = ensure_timezone(start_date)

        # Create aliases for tables
        aliased(Address)
        aliased(Address)

        # Determine the date format based on time frame
        if time_frame == TimeFrame.HOUR:
            date_format = "%Y-%m-%d %H:00:00"
        elif time_frame == TimeFrame.DAY:
            date_format = "%Y-%m-%d 00:00:00"
        elif time_frame == TimeFrame.WEEK:
            date_format = "%Y-%m-%d 00:00:00"  # We'll handle week grouping in Python
        else:  # month
            date_format = "%Y-%m-01 00:00:00"

        # Base query for alerts
        base_query = (
            db.query(
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
            .outerjoin(
                Analyzer,
                and_(
                    Analyzer._message_ident == Alert._ident,
                    Analyzer._parent_type == "A",
                    Analyzer._index == -1,
                ),
            )
            .filter(DetectTime.time >= start_date)
            .filter(DetectTime.time <= end_date)
        )

        # Apply filters
        if severity:
            base_query = base_query.filter(Impact.severity == severity)
        if classification:
            base_query = base_query.filter(Classification.text.like(f"%{classification}%"))
        if analyzer_name:
            base_query = base_query.filter(Analyzer.name == analyzer_name)

        # Group by time bucket and get counts
        results = (
            base_query
            .group_by(text("time_bucket"), Impact.severity, Classification.text, Analyzer.name)
            .order_by(text("time_bucket"))
            .all()
        )

        # Process results into timeline data points
        timeline_data = {}
        for result in results:
            time_str = result.time_bucket
            if not time_str:
                continue

            # Parse the timestamp
            timestamp = datetime.strptime(time_str, date_format).replace(tzinfo=UTC)
            
            # For weekly grouping, adjust timestamp to start of week
            if time_frame == TimeFrame.WEEK:
                # Adjust to Monday of the week
                timestamp = timestamp - timedelta(days=timestamp.weekday())

            # Initialize or get the data point
            if timestamp not in timeline_data:
                timeline_data[timestamp] = {
                    "timestamp": timestamp,
                    "total": 0,
                    "by_severity": {},
                    "by_classification": {},
                    "by_analyzer": {},
                }

            # Update counts
            data_point = timeline_data[timestamp]
            data_point["total"] += result.total

            if result.severity:
                if result.severity not in data_point["by_severity"]:
                    data_point["by_severity"][result.severity] = 0
                data_point["by_severity"][result.severity] += result.total
            
            if result.classification:
                if result.classification not in data_point["by_classification"]:
                    data_point["by_classification"][result.classification] = 0
                data_point["by_classification"][result.classification] += result.total
            
            if result.analyzer:
                if result.analyzer not in data_point["by_analyzer"]:
                    data_point["by_analyzer"][result.analyzer] = 0
                data_point["by_analyzer"][result.analyzer] += result.total

        # Convert to list and sort by timestamp
        timeline_points = [
            TimelineDataPoint(
                timestamp=timestamp,
                total=data["total"],
                by_severity=data["by_severity"],
                by_classification=data["by_classification"],
                by_analyzer=data["by_analyzer"]
            )
            for timestamp, data in timeline_data.items()
        ]
        timeline_points.sort(key=lambda x: x.timestamp)

        return TimelineResponse(
            time_frame=time_frame,
            start_date=start_date,
            end_date=end_date,
            data=timeline_points,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating timeline data: {str(e)}"
        )

@router.get("/summary", response_model=StatisticsSummary)
async def get_statistics_summary(
    time_range: int = Query(24, ge=1, le=720, description="Time range in hours to analyze"),
    db: Session = Depends(get_prelude_db),
) -> StatisticsSummary:
    """
    Get alert statistics summary for the specified time range.
    Includes total alerts, distribution by severity, classification, analyzer,
    and top source/target IPs.
    """
    try:
        # Calculate time range using utility function
        start_time, end_time = get_time_range(time_range)

        # Create aliases for source and target addresses
        source_addr = aliased(Address)
        target_addr = aliased(Address)

        # Base query for alerts within time range
        base_query = (
            db.query(Alert)
            .join(DetectTime, Alert._ident == DetectTime._message_ident)
            .filter(DetectTime.time >= start_time)
            .filter(DetectTime.time <= end_time)
        )

        # Get total alerts
        total_alerts = base_query.distinct().count()

        # Get alerts by severity
        alerts_by_severity = (
            base_query
            .outerjoin(Impact, Impact._message_ident == Alert._ident)
            .group_by(Impact.severity)
            .with_entities(Impact.severity, func.count(Alert._ident.distinct()))
            .all()
        )
        severity_distribution = {
            severity: count for severity, count in alerts_by_severity if severity
        }

        # Get alerts by classification
        alerts_by_classification = (
            base_query
            .outerjoin(Classification, Classification._message_ident == Alert._ident)
            .group_by(Classification.text)
            .with_entities(Classification.text, func.count(Alert._ident.distinct()))
            .all()
        )
        classification_distribution = {
            classification: count 
            for classification, count in alerts_by_classification 
            if classification
        }

        # Get alerts by analyzer
        alerts_by_analyzer = (
            base_query
            .outerjoin(
                Analyzer,
                and_(
                    Analyzer._message_ident == Alert._ident,
                    Analyzer._parent_type == "A",
                    Analyzer._index == -1,
                ),
            )
            .group_by(Analyzer.name)
            .with_entities(Analyzer.name, func.count(Alert._ident.distinct()))
            .all()
        )
        analyzer_distribution = {
            analyzer: count for analyzer, count in alerts_by_analyzer if analyzer
        }

        # Get top source IPs
        alerts_by_source_ip = (
            base_query
            .outerjoin(
                source_addr,
                and_(
                    source_addr._message_ident == Alert._ident,
                    source_addr._parent_type == "S",
                    source_addr.category == "ipv4-addr",
                ),
            )
            .group_by(source_addr.address)
            .with_entities(source_addr.address, func.count(Alert._ident.distinct()))
            .order_by(func.count(Alert._ident.distinct()).desc())
            .limit(10)
            .all()
        )
        source_ip_distribution = {
            ip: count for ip, count in alerts_by_source_ip if ip
        }

        # Get top target IPs
        alerts_by_target_ip = (
            base_query
            .outerjoin(
                target_addr,
                and_(
                    target_addr._message_ident == Alert._ident,
                    target_addr._parent_type == "T",
                    target_addr.category == "ipv4-addr",
                ),
            )
            .group_by(target_addr.address)
            .with_entities(target_addr.address, func.count(Alert._ident.distinct()))
            .order_by(func.count(Alert._ident.distinct()).desc())
            .limit(10)
            .all()
        )
        target_ip_distribution = {
            ip: count for ip, count in alerts_by_target_ip if ip
        }

        return StatisticsSummary(
            total_alerts=total_alerts,
            alerts_by_severity=severity_distribution,
            alerts_by_classification=classification_distribution,
            alerts_by_analyzer=analyzer_distribution,
            alerts_by_source_ip=source_ip_distribution,
            alerts_by_target_ip=target_ip_distribution,
            time_range_hours=time_range,
            start_time=start_time,
            end_time=end_time,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating statistics summary: {str(e)}"
        ) 