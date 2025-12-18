"""
Export routes - streaming CSV export with server-side cursors.
"""

import csv
from datetime import datetime, timedelta
from enum import Enum
from io import StringIO
from typing import Annotated, Iterator

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse

from app.core.datetime_utils import ensure_timezone, get_current_time
from app.repositories.alerts import AlertRepository, get_alert_repository
from app.schemas.filters import AlertFilterParams
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
    Properly closes the result set to avoid unbuffered result warnings.
    """
    output = StringIO()
    writer = csv.writer(output)

    try:
        # Write header row and yield it
        writer.writerow(header)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Write data rows one by one
        for row in results:
            # In SQLAlchemy 2.0 with labeled columns, we can access by attribute name
            # The labels we set in the query: detect_time, create_time, classification_text, etc.
            detect_time_str = format_iso_datetime(getattr(row, "detect_time", None))
            create_time_str = format_iso_datetime(getattr(row, "create_time", None))

            writer.writerow(
                [
                    str(row[0]),  # _ident (first column) - ensure it's a string
                    row[1],  # messageid (second column)
                    detect_time_str,
                    create_time_str,
                    getattr(row, "classification_text", "") or "",
                    getattr(row, "severity", "") or "",
                    getattr(row, "source_ipv4", "") or "",
                    getattr(row, "target_ipv4", "") or "",
                    getattr(row, "analyzer_name", "") or "",
                    getattr(row, "analyzer_host", "") or "",
                    getattr(row, "analyzer_model", "") or "",
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
    finally:
        # Ensure the result set is properly closed
        # This prevents "unbuffered result was left incomplete" warnings
        if hasattr(results, "close"):
            results.close()


@router.get("/alerts/{format}")
async def export_alerts(
    repo: Annotated[AlertRepository, Depends(get_alert_repository)],
    format: ExportFormat = Path(..., description="Export format (csv)"),
    alert_ids: list[int] | None = Query(None, description="Specific alert IDs"),
    start_date: datetime | None = Query(None, description="Start date (UTC)"),
    end_date: datetime | None = Query(None, description="End date (UTC)"),
    severity: str | None = Query(None, description="Filter by severity"),
    classification: str | None = Query(None, description="Filter by classification"),
    source_ip: str | None = Query(
        None, description="Filter by source IP or CIDR (e.g., 192.168.0.0/16)"
    ),
    target_ip: str | None = Query(
        None, description="Filter by target IP or CIDR (e.g., 10.0.0.0/8)"
    ),
    server: str | None = Query(None, description="Filter by server"),
    hours_back: int | None = Query(None, description="Past N hours (overrides dates)"),
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

    if format != ExportFormat.CSV:
        raise HTTPException(
            status_code=501, detail=f"Export format '{format}' is not yet supported"
        )

    # Build filter params - only used if alert_ids not provided
    filters = AlertFilterParams(
        severity=severity,
        classification=classification,
        start_date=ensure_timezone(start_date),
        end_date=ensure_timezone(end_date),
        source_ip=source_ip,
        target_ip=target_ip,
        server=server,
    )

    # Parse alert_ids if provided (already int from Query, but validate)
    parsed_alert_ids = [aid for aid in (alert_ids or []) if isinstance(aid, int)]

    results = repo.get_export_stream(
        filters=filters,
        alert_ids=parsed_alert_ids or None,
    )

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
    headers = {"Content-Disposition": "attachment; filename=alerts.csv"}
    return StreamingResponse(
        generate_csv(results, header), media_type="text/csv", headers=headers
    )
