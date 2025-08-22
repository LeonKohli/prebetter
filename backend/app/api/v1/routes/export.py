from fastapi import APIRouter, Depends, Query, Path, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, Iterator
from datetime import datetime, timedelta
import csv
from io import StringIO
from enum import Enum

from app.database.config import (
    get_prelude_db, 
    apply_standard_alert_filters,
)
from app.database.query_builders import build_alert_base_query
from app.core.datetime_utils import ensure_timezone, get_current_time
from app.models.prelude import (
    Alert,
    Impact,
    Classification,
    DetectTime,
    Analyzer,
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
        # In SQLAlchemy 2.0 with labeled columns, we can access by attribute name
        # The labels we set in the query: detect_time, create_time, classification_text, etc.
        detect_time_str = format_iso_datetime(getattr(row, 'detect_time', None))
        create_time_str = format_iso_datetime(getattr(row, 'create_time', None))

        writer.writerow(
            [
                str(row[0]),  # _ident (first column) - ensure it's a string
                row[1],  # messageid (second column)
                detect_time_str,
                create_time_str,
                getattr(row, 'classification_text', "") or "",
                getattr(row, 'severity', "") or "",
                getattr(row, 'source_ipv4', "") or "",
                getattr(row, 'target_ipv4', "") or "",
                getattr(row, 'analyzer_name', "") or "",
                getattr(row, 'analyzer_host', "") or "",
                getattr(row, 'analyzer_model', "") or "",
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

    # Get base query from query builder - this already has all the fields we need!
    query, models = build_alert_base_query(db)

    # Apply additional filter for alert IDs FIRST (before other filters)
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
    
    # Only apply other filters if we're not filtering by specific alert IDs
    # This ensures we get all requested alerts even if they lack some joined data
    if not alert_ids:
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

    # Order by alert ID descending and add limit for safety
    # We can't reliably order by DetectTime.time since it might be NULL for some alerts
    query = query.order_by(Alert._ident.desc()).limit(50000)
    
    # Use SQLAlchemy 2.0 execution options for streaming
    # yield_per enables server-side cursors and limits buffer size
    # We use partitions() to ensure the cursor is properly managed
    query = query.execution_options(yield_per=1000)
    
    # Execute the query - returns a Result object that can be iterated
    results = db.execute(query)

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
