from fastapi import APIRouter, Depends, Query, Response, Path
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime
import csv
from io import StringIO
from enum import Enum

from ....database.config import get_prelude_db
from ....models.prelude import (
    Alert,
    Impact,
    Classification,
    Address,
    DetectTime,
    Analyzer,
    Node,
    CreateTime,
)
from ..routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

class ExportFormat(str, Enum):
    CSV = "csv"

@router.get("/alerts/{format}")
async def export_alerts(
    format: ExportFormat = Path(..., description="Export format (currently only supports 'csv')"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    severity: Optional[str] = None,
    classification: Optional[str] = None,
    source_ip: Optional[str] = None,
    target_ip: Optional[str] = None,
    analyzer_model: Optional[str] = None,
    db: Session = Depends(get_prelude_db),
) -> Response:
    """Export alerts in the specified format with filtering options."""
    if format != ExportFormat.CSV:
        raise NotImplementedError(f"Export format '{format}' is not yet supported")

    # Create aliases for source and target addresses
    source_addr = aliased(Address)
    target_addr = aliased(Address)

    # Base query for alerts with essential joins
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
        .outerjoin(CreateTime, and_(CreateTime._message_ident == Alert._ident, CreateTime._parent_type == "A"))
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        .outerjoin(
            source_addr,
            and_(
                source_addr._message_ident == Alert._ident,
                source_addr._parent_type == "S",
                source_addr.category == "ipv4-addr",
            ),
        )
        .outerjoin(
            target_addr,
            and_(
                target_addr._message_ident == Alert._ident,
                target_addr._parent_type == "T",
                target_addr.category == "ipv4-addr",
            ),
        )
        .outerjoin(
            Analyzer,
            and_(
                Analyzer._message_ident == Alert._ident,
                Analyzer._parent_type == "A",
                Analyzer._index == -1,
            ),
        )
        .outerjoin(
            Node,
            and_(
                Node._message_ident == Alert._ident,
                Node._parent_type == "A",
                Node._parent0_index == -1,
            ),
        )
    )

    # Apply filters
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

    # Execute query
    results = query.all()

    # Create CSV file in memory
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
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
        "Analyzer Model"
    ])

    # Write data rows
    for row in results:
        writer.writerow([
            row._ident,
            row.messageid,
            row.detect_time.isoformat() if row.detect_time else "",
            row.create_time.isoformat() if row.create_time else "",
            row.classification_text or "",
            row.severity or "",
            row.source_ipv4 or "",
            row.target_ipv4 or "",
            row.analyzer_name or "",
            row.analyzer_host or "",
            row.analyzer_model or ""
        ])

    # Create response with CSV file
    response = Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=alerts.{format}"
        }
    )

    return response
