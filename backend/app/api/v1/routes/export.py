from fastapi import APIRouter, Depends, Query, Path, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, Iterator
from datetime import datetime
import csv
from io import StringIO
from enum import Enum

from ....database.config import get_prelude_db, apply_standard_alert_filters
from ....database.query_builders import build_alert_base_query
from ....models.prelude import (
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
        writer.writerow(
            [
                row._ident,
                row.messageid,
                row.detect_time.isoformat() + 'Z' if row.detect_time else "",
                row.create_time.isoformat() + 'Z' if row.create_time else "",
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

    # Get base query from query builder
    query, models = build_alert_base_query(db)
    
    # Modify the query to select only the fields we need for export
    # (We're not using build_alert_base_query directly to avoid selecting unnecessary fields)
    # Use DISTINCT ON to ensure we get exactly one row per alert ID
    query = query.with_entities(
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
    ).distinct(Alert._ident)

    # Apply standard filters
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
        Analyzer=Analyzer
    )
    
    # Apply additional filter for alert IDs (this is not part of standard filters)
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
            query = query.filter(Alert._ident.in_(alert_id_ints))

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