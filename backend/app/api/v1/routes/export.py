from fastapi import APIRouter, Depends, Query, Path, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_
from typing import Optional, Iterator
from datetime import datetime, UTC
import csv
from io import StringIO
from enum import Enum

from app.database.config import get_prelude_db
from app.models.prelude import (
    Alert,
    Impact,
    Classification,
    Address,
    DetectTime,
    Analyzer,
    Node,
    CreateTime,
)
from app.api.v1.routes.auth import get_current_user
from app.core.datetime_utils import ensure_timezone, format_datetime

router = APIRouter(dependencies=[Depends(get_current_user)])


class ExportFormat(str, Enum):
    CSV = "csv"


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
        # Ensure timezone information is preserved using utility function
        detect_time = ensure_timezone(row.detect_time)
        create_time = ensure_timezone(row.create_time)
        
        writer.writerow(
            [
                row._ident,
                row.messageid,
                detect_time.isoformat() if detect_time else "",
                create_time.isoformat() if create_time else "",
                row.classification_text or "",
                row.severity or "",
                row.source_ipv4 or "",
                row.target_ipv4 or "",
                row.analyzer_name or "",
                row.analyzer_host or "",
                row.analyzer_model or "",
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
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    severity: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    source_ip: Optional[str] = Query(None),
    target_ip: Optional[str] = Query(None),
    analyzer_model: Optional[str] = Query(None),
    db: Session = Depends(get_prelude_db),
) -> StreamingResponse:
    """Export alerts in CSV format with filtering options."""
    if format != ExportFormat.CSV:
        raise HTTPException(
            status_code=501, detail=f"Export format '{format}' is not yet supported"
        )

    # Ensure start_date and end_date are timezone-aware using utility function
    start_date = ensure_timezone(start_date)
    end_date = ensure_timezone(end_date)

    # Create aliases for source and target addresses
    source_addr = aliased(Address)
    target_addr = aliased(Address)

    # Base query for alerts with necessary joins
    query = (
        db.query(
            Alert._ident,
            Alert.messageid,
            DetectTime.time.label("detect_time"),
            CreateTime.time.label("create_time"),
            Classification.text.label("classification_text"),
            Impact.severity,
            source_addr.address.label("source_ipv4"),
            target_addr.address.label("target_ipv4"),
            Analyzer.name.label("analyzer_name"),
            Node.name.label("analyzer_host"),
            Analyzer.model.label("analyzer_model"),
        )
        .join(DetectTime, Alert._ident == DetectTime._message_ident)
        .outerjoin(
            CreateTime,
            and_(
                CreateTime._message_ident == Alert._ident,
                CreateTime._parent_type == "A",
            ),
        )
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        .outerjoin(
            source_addr,
            and_(
                source_addr._message_ident == Alert._ident,
                source_addr._parent_type == "S",  # Explicitly limit to source
                source_addr._parent0_index == -1,  # Primary source entry
                source_addr._index == -1,          # Final filter for primary address
                source_addr.category == "ipv4-addr",
            ),
        )
        .outerjoin(
            target_addr,
            and_(
                target_addr._message_ident == Alert._ident,
                target_addr._parent_type == "T",  # Explicitly limit to target
                target_addr._parent0_index == -1,  # Primary target entry
                target_addr._index == -1,          # Final filter for primary address
                target_addr.category == "ipv4-addr",
            ),
        )
        .outerjoin(
            Analyzer,
            and_(
                Analyzer._message_ident == Alert._ident,
                Analyzer._parent_type == "A",
                Analyzer._index == -1,  # Primary analyzer
            ),
        )
        .outerjoin(
            Node,
            and_(
                Node._message_ident == Alert._ident,
                Node._parent_type == "A",
                Node._parent0_index == -1,  # Primary node entry
            ),
        )
    )

    # Apply filters
    if alert_ids:
        query = query.filter(Alert._ident.in_(alert_ids))
    if severity:
        query = query.filter(Impact.severity == severity)
    if classification:
        query = query.filter(Classification.text.like(f"%{classification}%"))
    if start_date:
        query = query.filter(DetectTime.time >= start_date)
    if end_date:
        query = query.filter(DetectTime.time <= end_date)
    if source_ip:
        query = query.filter(func.binary(source_addr.address) == source_ip)
    if target_ip:
        query = query.filter(func.binary(target_addr.address) == target_ip)
    if analyzer_model:
        query = query.filter(Analyzer.model == analyzer_model)

    # Order by detect time descending
    query = query.order_by(DetectTime.time.desc())

    # Use yield_per to fetch rows in batches instead of loading all at once
    results = query.yield_per(1000)

    # Define CSV header row
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
    csv_stream = generate_csv(results, header)
    headers = {"Content-Disposition": "attachment; filename=alerts.csv"}
    return StreamingResponse(csv_stream, media_type="text/csv", headers=headers)