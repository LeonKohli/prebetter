from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, select, text, literal_column, desc, asc
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from enum import Enum
from ...database.config import get_db
from ...models.prelude import (
    Alert, Impact, Classification, Address, DetectTime,
    Analyzer, Node, Reference, Service, AdditionalData,
    CreateTime, Process, Source, Target
)
from ...schemas.prelude import (
    AlertListResponse, AlertListItem, AlertDetail,
    TimeInfo, NetworkInfo, AnalyzerInfo, NodeInfo,
    ProcessInfo, ReferenceInfo, ServiceInfo
)

router = APIRouter()

class SortField(str, Enum):
    DETECT_TIME = "detect_time"
    CREATE_TIME = "create_time"
    SEVERITY = "severity"
    CLASSIFICATION = "classification"

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

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
    target_ip: Optional[str] = None,
    analyzer_name: Optional[str] = None,
    impact_type: Optional[str] = None,
    sort_by: SortField = Query(SortField.DETECT_TIME, description="Field to sort by"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order")
):
    """
    Get a list of alerts with essential information:
    - Alert ID and timing
    - Classification
    - Severity
    - Source and target IPv4
    - Basic analyzer info
    
    Supports:
    - Pagination
    - Date range filtering
    - Multiple filter criteria
    - Sorting options
    """
    offset = (page - 1) * size

    # Base query for alerts
    query = (
        db.query(
            Alert._ident,
            Alert.messageid,
            # Create Time
            CreateTime.time.label('create_time'),
            CreateTime.usec.label('create_time_usec'),
            CreateTime.gmtoff.label('create_time_gmtoff'),
            # Detect Time
            DetectTime.time.label('detect_time'),
            DetectTime.usec.label('detect_time_usec'),
            DetectTime.gmtoff.label('detect_time_gmtoff'),
            # Classification and Impact
            Classification.text.label('classification'),
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
            Analyzer.name.label('analyzer_name'),
            Analyzer.model.label('analyzer_model'),
            Analyzer.manufacturer.label('analyzer_manufacturer'),
            Analyzer.version.label('analyzer_version'),
            literal_column('Prelude_Analyzer.class').label('analyzer_class'),
            Analyzer.ostype.label('analyzer_ostype'),
            Analyzer.osversion.label('analyzer_osversion'),
            # Node info
            Node.name.label('node_name'),
            Node.location.label('node_location'),
            Node.category.label('node_category'),
            # Process info
            Process.name.label('process_name'),
            Process.pid.label('process_pid'),
            Process.path.label('process_path')
        )
        .select_from(Alert)
        .outerjoin(CreateTime, and_(CreateTime._message_ident == Alert._ident, CreateTime._parent_type == 'A'))
        .outerjoin(DetectTime, DetectTime._message_ident == Alert._ident)
        .outerjoin(Classification, Classification._message_ident == Alert._ident)
        .outerjoin(Impact, Impact._message_ident == Alert._ident)
        .outerjoin(Analyzer, and_(Analyzer._message_ident == Alert._ident, Analyzer._parent_type == 'A', Analyzer._index == -1))
        .outerjoin(Node, and_(Node._message_ident == Alert._ident, Node._parent_type == 'A', Node._parent0_index == -1))
        .outerjoin(Process, and_(Process._message_ident == Alert._ident, Process._parent_type == 'A', Process._parent0_index == -1))
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
    if analyzer_name:
        query = query.filter(Analyzer.name == analyzer_name)
    if impact_type:
        query = query.filter(Impact.type == impact_type)

    # Apply sorting
    sort_column = None
    if sort_by == SortField.DETECT_TIME:
        sort_column = DetectTime.time
    elif sort_by == SortField.CREATE_TIME:
        sort_column = CreateTime.time
    elif sort_by == SortField.SEVERITY:
        sort_column = Impact.severity
    elif sort_by == SortField.CLASSIFICATION:
        sort_column = Classification.text

    if sort_column:
        query = query.order_by(desc(sort_column) if sort_order == SortOrder.DESC else asc(sort_column))

    # Get total count
    total = query.count()

    # Get paginated results
    results = query.order_by(Alert._ident.desc()).offset(offset).limit(size).all()

    # Process results
    alerts = []
    for result in results:
        node_info = None
        if result.node_name or result.node_location or result.node_category:
            node_info = NodeInfo(
                name=result.node_name,
                location=result.node_location,
                category=result.node_category
            )

        process_info = None
        if result.process_name or result.process_pid or result.process_path:
            process_info = ProcessInfo(
                name=result.process_name,
                pid=result.process_pid,
                path=result.process_path
            )

        analyzer_info = None
        if result.analyzer_name:
            analyzer_info = AnalyzerInfo(
                name=result.analyzer_name,
                node=node_info,
                model=result.analyzer_model,
                manufacturer=result.analyzer_manufacturer,
                version=result.analyzer_version,
                class_type=result.analyzer_class,
                ostype=result.analyzer_ostype,
                osversion=result.analyzer_osversion,
                process=process_info
            )

        alert_info = AlertListItem(
            alert_id=result[0],
            message_id=result[1],
            create_time=TimeInfo(
                time=result.create_time,
                usec=result.create_time_usec,
                gmtoff=result.create_time_gmtoff
            ) if result.create_time else None,
            detect_time=TimeInfo(
                time=result.detect_time,
                usec=result.detect_time_usec,
                gmtoff=result.detect_time_gmtoff
            ),
            classification_text=result.classification,
            severity=result.severity,
            source_ipv4=result.source_ipv4,
            target_ipv4=result.target_ipv4,
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
    db: Session = Depends(get_db),
    truncate_payload: bool = Query(False, description="Whether to truncate the payload data")
):
    """
    Get detailed information about a specific alert including:
    - Full timing information
    - Classification details
    - Impact details
    - Source and target information with complete network details
    - Detailed analyzer information
    - References
    - Services
    - Additional data
    
    Options:
    - truncate_payload: Truncate long payload data
    """
    try:
        # Get base alert information
        alert = (
            db.query(
                Alert,
                CreateTime,
                DetectTime,
                Classification,
                Impact
            )
            .outerjoin(CreateTime, and_(CreateTime._message_ident == Alert._ident, CreateTime._parent_type == 'A'))
            .outerjoin(DetectTime, DetectTime._message_ident == Alert._ident)
            .outerjoin(Classification, Classification._message_ident == Alert._ident)
            .outerjoin(Impact, Impact._message_ident == Alert._ident)
            .filter(Alert._ident == alert_id)
            .first()
        )

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Get source information with complete address details
        source_info = (
            db.query(Source, Address)
            .outerjoin(
                Address,
                and_(
                    Address._message_ident == Source._message_ident,
                    Address._parent_type == 'S',
                    Address._parent0_index == Source._index
                )
            )
            .filter(Source._message_ident == alert_id)
            .first()
        )

        # Get target information with complete address details
        target_info = (
            db.query(Target, Address)
            .outerjoin(
                Address,
                and_(
                    Address._message_ident == Target._message_ident,
                    Address._parent_type == 'T',
                    Address._parent0_index == Target._index
                )
            )
            .filter(Target._message_ident == alert_id)
            .first()
        )

        # Get analyzer information
        analyzer = (
            db.query(
                Analyzer,
                Node,
                Process
            )
            .outerjoin(
                Node,
                and_(
                    Node._message_ident == Analyzer._message_ident,
                    Node._parent_type == 'A',
                    Node._parent0_index == Analyzer._index
                )
            )
            .outerjoin(
                Process,
                and_(
                    Process._message_ident == Analyzer._message_ident,
                    Process._parent_type == 'A',
                    Process._parent0_index == Analyzer._index
                )
            )
            .filter(
                Analyzer._message_ident == alert_id,
                Analyzer._parent_type == 'A',
                Analyzer._index == -1
            )
            .first()
        )

        # Get references (prevent duplicates)
        references = (
            db.query(Reference)
            .filter(Reference._message_ident == alert_id)
            .distinct()
            .all()
        )

        # Get services (prevent duplicates)
        services = (
            db.query(Service)
            .filter(Service._message_ident == alert_id)
            .distinct()
            .all()
        )

        # Get additional data
        additional_data = {}
        add_data_rows = (
            db.query(AdditionalData)
            .filter(
                AdditionalData._message_ident == alert_id,
                AdditionalData._parent_type == 'A'
            )
            .all()
        )

        def clean_byte_string(value: str) -> str:
            """Clean byte string values by removing b'...' prefix and converting to proper type"""
            if not value:
                return None
            # Remove b'...' if present
            if value.startswith("b'") and value.endswith("'"):
                value = value[2:-1]
            # Try to convert to int if it's numeric
            try:
                if value.isdigit():
                    return str(int(value))
                return value
            except:
                return value

        for row in add_data_rows:
            try:
                if row.type in ['integer', 'real', 'character']:
                    additional_data[row.meaning] = clean_byte_string(str(row.data))
                elif row.type == 'byte-string':
                    if row.meaning == 'payload':
                        decoded = row.data.decode('utf-8', errors='ignore')
                        if truncate_payload and len(decoded) > 500:
                            decoded = decoded[:500] + "..."
                        additional_data[row.meaning] = decoded
                    else:
                        additional_data[row.meaning] = clean_byte_string(row.data.decode('utf-8', errors='ignore'))
                else:
                    additional_data[row.meaning] = str(row.data)
            except Exception as e:
                additional_data[row.meaning] = f"Error decoding data: {str(e)}"

        # Build source network info with complete address details
        source = None
        if source_info and source_info[1]:  # Check if Address info exists
            source = NetworkInfo(
                interface=source_info[0].interface,
                category=source_info[1].category,
                address=source_info[1].address,
                netmask=source_info[1].netmask,
                vlan_name=source_info[1].vlan_name,
                vlan_num=source_info[1].vlan_num,
                ident=source_info[1].ident,
                ip_version=next((int(d.data) for d in add_data_rows if d.meaning == 'ip_ver'), None),
                ip_hlen=next((int(d.data) for d in add_data_rows if d.meaning == 'ip_hlen'), None)
            )

        # Build target network info with complete address details
        target = None
        if target_info and target_info[1]:  # Check if Address info exists
            target = NetworkInfo(
                interface=target_info[0].interface,
                category=target_info[1].category,
                address=target_info[1].address,
                netmask=target_info[1].netmask,
                vlan_name=target_info[1].vlan_name,
                vlan_num=target_info[1].vlan_num,
                ident=target_info[1].ident,
                ip_version=next((int(d.data) for d in add_data_rows if d.meaning == 'ip_ver'), None),
                ip_hlen=next((int(d.data) for d in add_data_rows if d.meaning == 'ip_hlen'), None)
            )

        # Build analyzer info
        analyzer_info = None
        if analyzer:
            node_info = None
            if analyzer[1]:
                node_info = NodeInfo(
                    ident=analyzer[1].ident,
                    category=analyzer[1].category,
                    location=analyzer[1].location,
                    name=analyzer[1].name
                )

            process_info = None
            if analyzer[2]:
                process_info = ProcessInfo(
                    name=analyzer[2].name,
                    pid=analyzer[2].pid,
                    path=analyzer[2].path
                )

            analyzer_info = AnalyzerInfo(
                name=analyzer[0].name,
                node=node_info,
                model=analyzer[0].model,
                manufacturer=analyzer[0].manufacturer,
                version=analyzer[0].version,
                class_type=getattr(analyzer[0], 'class', None),
                ostype=analyzer[0].ostype,
                osversion=analyzer[0].osversion,
                process=process_info
            )

        # Remove duplicate services while preserving order
        seen_services = set()
        unique_services = []
        for svc in services:
            service_key = (svc.port, svc.iana_protocol_name, svc._parent_type)
            if service_key not in seen_services:
                seen_services.add(service_key)
                unique_services.append(svc)

        # Remove duplicate references while preserving order
        seen_refs = set()
        unique_refs = []
        for ref in references:
            ref_key = (ref.origin, ref.name, ref.url)
            if ref_key not in seen_refs:
                seen_refs.add(ref_key)
                unique_refs.append(ref)

        return AlertDetail(
            alert_id=alert[0]._ident,
            message_id=alert[0].messageid,
            create_time=TimeInfo(
                time=alert[1].time,
                usec=alert[1].usec,
                gmtoff=alert[1].gmtoff
            ) if alert[1] else None,
            detect_time=TimeInfo(
                time=alert[2].time,
                usec=alert[2].usec,
                gmtoff=alert[2].gmtoff
            ),
            classification_text=alert[3].text,
            classification_ident=alert[3].ident,
            severity=alert[4].severity if alert[4] else None,
            description=alert[4].description if alert[4] else None,
            completion=alert[4].completion if alert[4] else None,
            impact_type=alert[4].type if alert[4] else None,
            source=source,
            target=target,
            analyzer=analyzer_info,
            references=[
                ReferenceInfo(
                    origin=ref.origin,
                    name=ref.name,
                    url=ref.url,
                    meaning=ref.meaning
                )
                for ref in unique_refs
            ],
            services=[
                ServiceInfo(
                    port=svc.port,
                    protocol=svc.iana_protocol_name,
                    direction="source" if svc._parent_type == 'S' else "target"
                )
                for svc in unique_services
            ],
            additional_data=additional_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing alert: {str(e)}")

@router.get("/statistics/summary")
async def get_statistics_summary(
    db: Session = Depends(get_db),
    time_range: int = Query(24, description="Time range in hours to analyze")
):
    """Get summary statistics of alerts"""
    try:
        start_time = datetime.utcnow() - timedelta(hours=time_range)
        
        # Get severity distribution
        severity_stats = (
            db.query(
                Impact.severity,
                func.count(Alert._ident).label('count')
            )
            .join(Alert, Alert._ident == Impact._message_ident)
            .join(DetectTime, DetectTime._message_ident == Alert._ident)
            .filter(DetectTime.time >= start_time)
            .group_by(Impact.severity)
            .all()
        )

        # Get top classifications
        top_classifications = (
            db.query(
                Classification.text,
                func.count(Alert._ident).label('count')
            )
            .join(Alert, Alert._ident == Classification._message_ident)
            .join(DetectTime, DetectTime._message_ident == Alert._ident)
            .filter(DetectTime.time >= start_time)
            .group_by(Classification.text)
            .order_by(func.count(Alert._ident).desc())
            .limit(10)
            .all()
        )

        # Get top source IPs
        top_sources = (
            db.query(
                Address.address,
                func.count(Alert._ident).label('count')
            )
            .join(Alert, Alert._ident == Address._message_ident)
            .join(DetectTime, DetectTime._message_ident == Alert._ident)
            .filter(
                DetectTime.time >= start_time,
                Address._parent_type == 'S',
                Address.category == 'ipv4-addr'
            )
            .group_by(Address.address)
            .order_by(func.count(Alert._ident).desc())
            .limit(10)
            .all()
        )

        return {
            "time_range_hours": time_range,
            "severity_distribution": {
                severity: count for severity, count in severity_stats if severity
            },
            "top_classifications": {
                text: count for text, count in top_classifications
            },
            "top_source_ips": {
                ip: count for ip, count in top_sources
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating statistics: {str(e)}")

@router.get("/classifications/", response_model=List[str])
def read_unique_classifications(db: Session = Depends(get_db)):
    try:
        classifications = db.query(Classification.text).distinct().all()
        return [c[0] for c in classifications]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching classifications: {str(e)}")

@router.get("/impacts/severities/", response_model=List[str])
def read_unique_severities(db: Session = Depends(get_db)):
    try:
        severities = db.query(Impact.severity).distinct().all()
        return [s[0] for s in severities if s[0]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching severities: {str(e)}")

@router.get("/analyzers/", response_model=List[str])
def read_unique_analyzers(db: Session = Depends(get_db)):
    """Get list of unique analyzer names"""
    try:
        analyzers = db.query(Analyzer.name).distinct().all()
        return [a[0] for a in analyzers if a[0]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analyzers: {str(e)}") 