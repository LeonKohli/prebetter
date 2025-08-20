from fastapi import APIRouter, Depends, Query, Path, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, Iterator
from datetime import datetime, timedelta
import csv
from io import StringIO
from enum import Enum

from app.database.config import (
    get_prelude_db, 
    apply_standard_alert_filters,
    get_source_address_join_conditions,
    get_target_address_join_conditions,
    get_node_join_conditions,
    get_analyzer_join_conditions,
)
from app.database.query_builders import build_alert_base_query
from app.core.datetime_utils import ensure_timezone, get_current_time
from app.models.prelude import (
    Alert,
    Impact,
    Classification,
    DetectTime,
    Analyzer,
    Node,
    CreateTime,
)
from ..routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


class ExportFormat(str, Enum):
    CSV = "csv"


def format_iso_datetime(dt):
    """
    Format a datetime object to ISO 8601 format.
    Ensures proper timezone representation without duplicate information.
    """
    if dt is None:
        return ""

    # Ensure datetime has timezone info
    dt = ensure_timezone(dt)
    if dt is None:
        return ""
    # Return ISO format - the datetime.isoformat() method already handles timezone
    return dt.isoformat()


def generate_csv(results: Iterator, header: list) -> Iterator[str]:
    """
    A generator that yields CSV lines.
    """
    output = StringIO()
    writer = csv.writer(output)

    # Write header row and yield it
    writer.writerow(header)
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    # Write data rows one by one
    for row in results:
        # In SQLAlchemy 2.0, results come as Row objects with named attributes
        # Access by index or attribute name
        detect_time_str = format_iso_datetime(row[2] if len(row) > 2 else None)  # detect_time
        create_time_str = format_iso_datetime(row[3] if len(row) > 3 else None)  # create_time

        writer.writerow(
            [
                row[0],  # _ident
                row[1],  # messageid
                detect_time_str,
                create_time_str,
                row[4] or "" if len(row) > 4 else "",  # classification_text
                row[5] or "" if len(row) > 5 else "",  # severity
                row[6] or "" if len(row) > 6 else "",  # source_ipv4
                row[7] or "" if len(row) > 7 else "",  # target_ipv4
                row[8] or "" if len(row) > 8 else "",  # analyzer_name
                row[9] or "" if len(row) > 9 else "",  # analyzer_host
                row[10] or "" if len(row) > 10 else "",  # analyzer_model
            ]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)


@router.get("/alerts/{format}")
async def export_alerts(
    format: ExportFormat = Path(
        ..., description="Export format (currently only supports 'csv')"
    ),
    alert_ids: Optional[list[int]] = Query(
        None, description="List of specific alert IDs to export"
    ),
    start_date: Optional[datetime] = Query(
        None, description="Start date for filtering alerts"
    ),
    end_date: Optional[datetime] = Query(
        None, description="End date for filtering alerts"
    ),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    classification: Optional[str] = Query(None, description="Filter by classification"),
    source_ip: Optional[str] = Query(None, description="Filter by source IP address"),
    target_ip: Optional[str] = Query(None, description="Filter by target IP address"),
    analyzer_model: Optional[str] = Query(None, description="Filter by analyzer model"),
    hours_back: Optional[int] = Query(
        None,
        description="Export alerts from the past N hours (alternative to start/end dates)",
    ),
    db: Session = Depends(get_prelude_db),
) -> StreamingResponse:
    """
    Export alerts in the specified format.
    Supports filtering by criteria and exporting specific alert IDs.

    If hours_back is specified, it overrides start_date and end_date parameters.
    """
    # Handle the hours_back parameter if provided
    if hours_back is not None and hours_back > 0:
        end_date = get_current_time()
        start_date = end_date - timedelta(hours=hours_back)

    # Ensure dates have timezone information
    start_date = ensure_timezone(start_date)
    end_date = ensure_timezone(end_date)

    if format != ExportFormat.CSV:
        raise HTTPException(
            status_code=501, detail=f"Export format '{format}' is not yet supported"
        )

    # Get base query from query builder
    _, models = build_alert_base_query(db)

    # Build a new select query with only the fields we need for export
    from sqlalchemy import and_
    
    query = (
        select(
            Alert._ident,
            Alert.messageid,
            DetectTime.time.label("detect_time"),
            CreateTime.time.label("create_time"),
            Classification.text.label("classification_text"),
            Impact.severity,
            models["source_addr"].address.label("source_ipv4"),
            models["target_addr"].address.label("target_ipv4"),
            Analyzer.name.label("analyzer_name"),
            Node.name.label("analyzer_host"),
            Analyzer.model.label("analyzer_model"),
        )
        .select_from(Alert)
        .outerjoin(DetectTime, DetectTime._message_ident == Alert._ident)
        .outerjoin(CreateTime, CreateTime._message_ident == Alert._ident)
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        .outerjoin(
            models["source_addr"], 
            and_(
                models["source_addr"]._message_ident == Alert._ident,
                models["source_addr"]._parent_type == "S",
                models["source_addr"]._parent0_index == -1,
                models["source_addr"].category == "ipv4-addr",
            )
        )
        .outerjoin(
            models["target_addr"], 
            and_(
                models["target_addr"]._message_ident == Alert._ident,
                models["target_addr"]._parent_type == "T",
                models["target_addr"]._parent0_index == -1,
                models["target_addr"].category == "ipv4-addr",
            )
        )
        .outerjoin(
            Analyzer, 
            and_(
                Analyzer._message_ident == Alert._ident,
                Analyzer._parent_type == "A",
                Analyzer._index == -1,
            )
        )
        .outerjoin(
            Node, 
            and_(
                Node._message_ident == Alert._ident,
                Node._parent_type == "A",
                Node._parent0_index == -1,
            )
        )
        # Removed group_by as it's not needed for export - we want all data
        # .group_by(Alert._ident)
    )

    # Apply standard filters - explicitly pass model classes for filtering
    query = apply_standard_alert_filters(
        query=query,
        severity=severity,
        classification=classification,
        start_date=start_date,
        end_date=end_date,
        source_ip=source_ip,
        target_ip=target_ip,
        analyzer_model=analyzer_model,
        **models,
        Impact=Impact,
        Classification=Classification,
        DetectTime=DetectTime,
        Analyzer=Analyzer,
    )

    # Apply additional filter for alert IDs
    if alert_ids:
        # Convert to list if it's not already
        if not isinstance(alert_ids, list):
            alert_ids = [alert_ids]
        # Convert string IDs to integers if needed
        alert_id_ints = []
        for aid in alert_ids:
            try:
                alert_id_ints.append(int(aid))
            except (ValueError, TypeError):
                # Skip invalid IDs
                continue
        if alert_id_ints:
            query = query.where(Alert._ident.in_(alert_id_ints))

    # Order by detect time descending
    query = query.order_by(DetectTime.time.desc())
    
    # Add a reasonable limit to prevent memory issues
    # This can be made configurable later
    query = query.limit(10000)

    # Execute the query and fetch results
    results = db.execute(query).all()

    # Define CSV header row - match the exact order expected by tests
    header = [
        "Alert ID",
        "Message ID",
        "Detect Time",
        "Create Time",
        "Classification",
        "Severity",
        "Source IP",
        "Target IP",
        "Analyzer Name",
        "Analyzer Host",
        "Analyzer Model",
    ]

    # Create the streaming response using the CSV generator
    # Use alerts.csv as filename to match the tests
    headers = {"Content-Disposition": "attachment; filename=alerts.csv"}
    return StreamingResponse(
        generate_csv(results, header), media_type="text/csv", headers=headers
    )
