from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_, text
from ....database.config import get_db
from ....models.prelude import Alert, DetectTime, Impact, Classification, Analyzer, Node, Address
from ....schemas.prelude import TimelineResponse, TimelineDataPoint, GroupedAlertResponse, GroupedAlert, GroupedAlertDetail, StatisticsSummary
from enum import Enum
from fastapi import HTTPException

router = APIRouter()

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
    db: Session = Depends(get_db),
) -> TimelineResponse:
    """
    Get alert timeline data grouped by the specified time frame.
    Supports filtering by severity, classification, and analyzer.
    """
    try:
        # Set default time range if not provided
        if not end_date:
            end_date = datetime.now(UTC)
        if not start_date:
            if time_frame == TimeFrame.HOUR:
                start_date = end_date - timedelta(hours=24)
            elif time_frame == TimeFrame.DAY:
                start_date = end_date - timedelta(days=30)
            elif time_frame == TimeFrame.WEEK:
                start_date = end_date - timedelta(weeks=12)
            else:  # month
                start_date = end_date - timedelta(days=365)

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
                data_point["by_severity"][result.severity] = data_point["by_severity"].get(result.severity, 0) + result.total
            
            if result.classification:
                data_point["by_classification"][result.classification] = data_point["by_classification"].get(result.classification, 0) + result.total
            
            if result.analyzer:
                data_point["by_analyzer"][result.analyzer] = data_point["by_analyzer"].get(result.analyzer, 0) + result.total

        # Convert to list and sort by timestamp
        timeline_points = [
            TimelineDataPoint(**data)
            for data in timeline_data.values()
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

@router.get("/grouped", response_model=GroupedAlertResponse)
async def get_grouped_alerts(
    group_by: GroupBy,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> GroupedAlertResponse:
    # Default to last 7 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=7)

    # Base query
    base_query = db.query(Alert._ident).join(DetectTime, Alert._ident == DetectTime._message_ident)
    base_query = base_query.filter(DetectTime.time.between(start_date, end_date))

    # Add grouping based on group_by parameter
    if group_by == GroupBy.SEVERITY:
        query = (
            db.query(Impact.severity)
            .select_from(Alert)
            .join(DetectTime, Alert._ident == DetectTime._message_ident)
            .join(Impact, Impact._message_ident == Alert._ident)
            .filter(DetectTime.time.between(start_date, end_date))
            .group_by(Impact.severity)
        )
    elif group_by == GroupBy.CLASSIFICATION:
        query = (
            db.query(Classification.text)
            .select_from(Alert)
            .join(DetectTime, Alert._ident == DetectTime._message_ident)
            .join(Classification, Classification._message_ident == Alert._ident)
            .filter(DetectTime.time.between(start_date, end_date))
            .group_by(Classification.text)
        )
    elif group_by == GroupBy.ANALYZER:
        query = (
            db.query(Analyzer.name, Node.name)
            .select_from(Alert)
            .join(DetectTime, Alert._ident == DetectTime._message_ident)
            .join(Analyzer, and_(Analyzer._message_ident == Alert._ident, Analyzer._parent_type == "A"))
            .outerjoin(Node, and_(Node._message_ident == Alert._ident, Node._parent_type == "A"))
            .filter(DetectTime.time.between(start_date, end_date))
            .group_by(Analyzer.name, Node.name)
        )

    # Get total count
    total = len(list(query))

    # Apply pagination
    offset = (page - 1) * size
    results = list(query.offset(offset).limit(size))

    # Convert results to response format
    groups = []
    for result in results:
        if group_by == GroupBy.ANALYZER:
            analyzer_name, node_name = result
            group_detail = GroupedAlertDetail(
                classification=f"{analyzer_name} ({node_name})" if node_name else analyzer_name,
                count=db.query(func.count(Alert._ident.distinct()))
                .join(Analyzer, and_(Analyzer._message_ident == Alert._ident, Analyzer._parent_type == "A"))
                .filter(Analyzer.name == analyzer_name)
                .scalar(),
                analyzer=[analyzer_name],
                analyzer_host=[node_name] if node_name else [],
                time=db.query(DetectTime.time)
                .join(Alert, Alert._ident == DetectTime._message_ident)
                .join(Analyzer, and_(Analyzer._message_ident == Alert._ident, Analyzer._parent_type == "A"))
                .filter(Analyzer.name == analyzer_name)
                .order_by(DetectTime.time.desc())
                .first()[0]
            )
        else:
            group_value = result[0] if isinstance(result, tuple) else result
            group_detail = GroupedAlertDetail(
                classification=str(group_value),
                count=db.query(func.count(Alert._ident.distinct()))
                .select_from(Alert)
                .join(DetectTime, Alert._ident == DetectTime._message_ident)
                .join(Impact if group_by == GroupBy.SEVERITY else Classification,
                      (Impact if group_by == GroupBy.SEVERITY else Classification)._message_ident == Alert._ident)
                .filter(
                    DetectTime.time.between(start_date, end_date),
                    getattr(Impact if group_by == GroupBy.SEVERITY else Classification, 
                           "severity" if group_by == GroupBy.SEVERITY else "text") == group_value
                )
                .scalar(),
                analyzer=[],
                analyzer_host=[],
                time=db.query(DetectTime.time)
                .select_from(Alert)
                .join(DetectTime, Alert._ident == DetectTime._message_ident)
                .join(Impact if group_by == GroupBy.SEVERITY else Classification,
                      (Impact if group_by == GroupBy.SEVERITY else Classification)._message_ident == Alert._ident)
                .filter(
                    getattr(Impact if group_by == GroupBy.SEVERITY else Classification,
                           "severity" if group_by == GroupBy.SEVERITY else "text") == group_value
                )
                .order_by(DetectTime.time.desc())
                .first()[0]
            )
        
        groups.append(GroupedAlert(
            total_count=group_detail.count,
            alerts=[group_detail]
        ))

    return GroupedAlertResponse(
        total=total,
        groups=groups,
        page=page,
        size=size
    )

@router.get("/summary", response_model=StatisticsSummary)
async def get_statistics_summary(
    time_range: int = Query(24, ge=1, le=720, description="Time range in hours to analyze"),
    db: Session = Depends(get_db),
) -> StatisticsSummary:
    """
    Get alert statistics summary for the specified time range.
    Includes total alerts, distribution by severity, classification, analyzer,
    and top source/target IPs.
    """
    try:
        # Calculate time range
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=time_range)

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