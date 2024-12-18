from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, select, text, literal_column
from typing import List, Optional
from datetime import datetime
from ...database.config import get_db
from ...models.prelude import (
    Alert, Impact, Classification, Address, DetectTime,
    Analyzer, Node, Reference, Service, AdditionalData
)
from ...schemas.prelude import (
    AlertListResponse, AlertListItem, AlertDetail
)

router = APIRouter()

@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    db: Session = Depends(get_db),
    page: int = Query(1, gt=0),
    size: int = Query(20, gt=0, le=100),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    severity: Optional[str] = None,
    classification: Optional[str] = None,
    source_ip: Optional[str] = None,
    target_ip: Optional[str] = None
):
    """
    Get a list of alerts with essential information:
    - Alert ID and timing
    - Classification
    - Severity
    - Source and target IPv4
    - Basic analyzer info (name and host)
    """
    # Calculate offset
    offset = (page - 1) * size

    # Primary Analyzer subquery (index = -1 for primary analyzer)
    analyzer_subq = (
        db.query(
            Analyzer._message_ident.label('alert_id'),
            Analyzer.name.label('analyzer_name'),
            Node.name.label('host')
        )
        .select_from(Analyzer)
        .outerjoin(
            Node,
            and_(
                Node._message_ident == Analyzer._message_ident,
                Node._parent_type == 'A',
                Node._parent0_index == -1
            )
        )
        .filter(
            and_(
                Analyzer._parent_type == 'A',
                Analyzer._index == -1
            )
        )
        .subquery()
    )

    # Base query for alerts list
    query = (
        db.query(
            Alert._ident,
            DetectTime.time,
            Classification.text,
            Impact.severity,
            # Source IPv4
            db.query(func.min(Address.address))
            .filter(
                Address._message_ident == Alert._ident,
                Address._parent_type == 'S',
                Address.category == 'ipv4-addr'
            )
            .scalar_subquery()
            .label('source_ipv4'),
            # Target IPv4
            db.query(func.min(Address.address))
            .filter(
                Address._message_ident == Alert._ident,
                Address._parent_type == 'T',
                Address.category == 'ipv4-addr'
            )
            .scalar_subquery()
            .label('target_ipv4'),
            # Analyzer info
            analyzer_subq.c.analyzer_name,
            analyzer_subq.c.host
        )
        .select_from(Alert)
        .outerjoin(DetectTime, DetectTime._message_ident == Alert._ident)
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        .outerjoin(analyzer_subq, analyzer_subq.c.alert_id == Alert._ident)
    )

    # Apply filters
    if start_date:
        query = query.filter(DetectTime.time >= start_date)
    if end_date:
        query = query.filter(DetectTime.time <= end_date)
    if severity:
        query = query.filter(Impact.severity == severity)
    if classification:
        query = query.filter(Classification.text.contains(classification))
    if source_ip:
        query = query.join(
            Address,
            and_(
                Address._message_ident == Alert._ident,
                Address._parent_type == 'S',
                Address.category == 'ipv4-addr'
            )
        ).filter(Address.address == source_ip)
    if target_ip:
        query = query.join(
            Address,
            and_(
                Address._message_ident == Alert._ident,
                Address._parent_type == 'T',
                Address.category == 'ipv4-addr'
            )
        ).filter(Address.address == target_ip)

    # Get total count
    total_query = db.query(Alert._ident)
    if any([start_date, end_date, severity, classification, source_ip, target_ip]):
        total = query.count()
    else:
        total = total_query.count()

    # Get paginated results
    results = query.order_by(Alert._ident.desc()).offset(offset).limit(size).all()

    # Process results
    alerts = []
    for result in results:
        analyzer_info = None
        if result[6]:  # If analyzer name exists
            analyzer_info = {
                "name": result[6],
                "host": result[7]
            }

        alert_info = AlertListItem(
            alert_id=result[0],
            detect_time=result[1],
            classification_text=result[2],
            severity=result[3],
            source_ipv4=result[4],
            target_ipv4=result[5],
            analyzer=analyzer_info
        )
        alerts.append(alert_info)

    return AlertListResponse(
        total=total,
        items=alerts,
        page=page,
        size=size
    )

@router.get("/alerts/{alert_id}", response_model=AlertDetail)
async def get_alert_detail(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific alert:
    - Full timing information
    - Classification with rule ID
    - Severity and Impact details
    - Source and target IPv4
    - Detailed analyzer information
    - References (CVE, Bugtraq, etc.)
    - Service information
    - Additional data (Snort rule details, payload)
    """
    # Get base alert information
    alert = (
        db.query(
            Alert,
            DetectTime,
            Classification,
            Impact
        )
        .outerjoin(DetectTime, DetectTime._message_ident == Alert._ident)
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        .filter(Alert._ident == alert_id)
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Get source and target addresses
    source_ipv4 = (
        db.query(Address.address)
        .filter(
            Address._message_ident == alert_id,
            Address._parent_type == 'S',
            Address.category == 'ipv4-addr'
        )
        .first()
    )

    target_ipv4 = (
        db.query(Address.address)
        .filter(
            Address._message_ident == alert_id,
            Address._parent_type == 'T',
            Address.category == 'ipv4-addr'
        )
        .first()
    )

    # Get analyzer information
    analyzer = (
        db.query(Analyzer)
        .outerjoin(
            Node,
            and_(
                Node._message_ident == Analyzer._message_ident,
                Node._parent_type == 'A',
                Node._parent0_index == Analyzer._index
            )
        )
        .filter(
            Analyzer._message_ident == alert_id,
            Analyzer._parent_type == 'A',
            Analyzer._index == -1
        )
        .first()
    )

    analyzer_host = (
        db.query(Node.name)
        .filter(
            Node._message_ident == alert_id,
            Node._parent_type == 'A',
            Node._parent0_index == -1
        )
        .first()
    )

    # Get references
    references = (
        db.query(Reference)
        .filter(Reference._message_ident == alert_id)
        .all()
    )

    # Get services
    services = (
        db.query(Service)
        .filter(Service._message_ident == alert_id)
        .all()
    )

    # Get additional data
    add_data = {
        'snort_rule_sid': None,
        'snort_rule_rev': None,
        'ip_version': None,
        'payload_preview': None
    }

    add_data_rows = (
        db.query(AdditionalData)
        .filter(
            AdditionalData._message_ident == alert_id,
            AdditionalData._parent_type == 'A'
        )
        .all()
    )

    for row in add_data_rows:
        if row.meaning == 'snort_rule_sid':
            add_data['snort_rule_sid'] = int(row.data)
        elif row.meaning == 'snort_rule_rev':
            add_data['snort_rule_rev'] = int(row.data)
        elif row.meaning == 'ip_ver':
            add_data['ip_version'] = int(row.data)
        elif row.meaning == 'payload':
            add_data['payload_preview'] = row.data[:200].decode('utf-8', errors='ignore')

    # Construct analyzer info
    analyzer_info = None
    if analyzer:
        analyzer_info = {
            "name": analyzer.name,
            "host": analyzer_host[0] if analyzer_host else None,
            "analyzer_id": analyzer.analyzerid,
            "manufacturer": analyzer.manufacturer,
            "model": analyzer.model,
            "version": analyzer.version,
            "class_type": getattr(analyzer, 'class', None),
            "ostype": analyzer.ostype,
            "osversion": analyzer.osversion
        }

    # Construct response
    return AlertDetail(
        alert_id=alert[0]._ident,
        detect_time=alert[1].time,
        detect_time_usec=alert[1].usec,
        detect_time_gmtoff=alert[1].gmtoff,
        classification_text=alert[2].text,
        classification_ident=alert[2].ident,
        severity=alert[3].severity if alert[3] else None,
        description=alert[3].description if alert[3] else None,
        completion=alert[3].completion if alert[3] else None,
        impact_type=alert[3].type if alert[3] else None,
        source_ipv4=source_ipv4[0] if source_ipv4 else None,
        target_ipv4=target_ipv4[0] if target_ipv4 else None,
        analyzer=analyzer_info,
        references=[
            {
                "origin": ref.origin,
                "name": ref.name,
                "url": ref.url
            }
            for ref in references
        ],
        services=[
            {
                "port": svc.port,
                "protocol": svc.iana_protocol_name,
                "direction": "source" if svc._parent_type == 'S' else "target"
            }
            for svc in services
        ],
        additional_data=add_data if any(add_data.values()) else None
    )

@router.get("/classifications/", response_model=List[str])
def read_unique_classifications(db: Session = Depends(get_db)):
    classifications = db.query(Classification.text).distinct().all()
    return [c[0] for c in classifications]

@router.get("/impacts/severities/", response_model=List[str])
def read_unique_severities(db: Session = Depends(get_db)):
    severities = db.query(Impact.severity).distinct().all()
    return [s[0] for s in severities if s[0]] 