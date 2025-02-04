from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_, literal_column, tuple_, distinct
from typing import Optional
from datetime import datetime
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
    Reference,
    Service,
    AdditionalData,
    CreateTime,
    Process,
    Source,
    Target,
)
from ....schemas.prelude import (
    AlertListResponse,
    AlertListItem,
    AlertDetail,
    TimeInfo,
    NetworkInfo,
    AnalyzerInfo,
    NodeInfo,
    ProcessInfo,
    ReferenceInfo,
    ServiceInfo,
    GroupedAlertResponse,
    GroupedAlert,
    GroupedAlertDetail,
)

router = APIRouter()

class SortField(str, Enum):
    DETECT_TIME = "detect_time"
    CREATE_TIME = "create_time"
    SEVERITY = "severity"
    CLASSIFICATION = "classification"
    SOURCE_IP = "source_ip"
    TARGET_IP = "target_ip"
    ANALYZER = "analyzer"
    ALERT_ID = "alert_id"

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    sort_by: SortField = Query(SortField.DETECT_TIME, description="Field to sort by"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order (asc/desc)"),
    severity: Optional[str] = None,
    classification: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    source_ip: Optional[str] = None,
    target_ip: Optional[str] = None,
    analyzer_model: Optional[str] = None,
    db: Session = Depends(get_prelude_db),
) -> AlertListResponse:
    # Create aliases for source and target addresses
    source_addr = aliased(Address)
    target_addr = aliased(Address)

    # Base query for alerts with essential joins
    query = (
        db.query(
            Alert._ident,
            Alert.messageid,
            DetectTime.time.label("detect_time"),
            DetectTime.usec.label("detect_time_usec"),
            DetectTime.gmtoff.label("detect_time_gmtoff"),
            CreateTime.time.label("create_time"),
            CreateTime.usec.label("create_time_usec"),
            CreateTime.gmtoff.label("create_time_gmtoff"),
            Classification.text.label("classification_text"),
            Impact.severity,
            source_addr.address.label("source_ipv4"),
            target_addr.address.label("target_ipv4"),
            Analyzer.name.label("analyzer_name"),
            Node.name.label("analyzer_host"),
            Analyzer.model.label("analyzer_model"),
            Analyzer.manufacturer.label("analyzer_manufacturer"),
            Analyzer.version.label("analyzer_version"),
            literal_column("Prelude_Analyzer.class").label("analyzer_class"),
            Analyzer.ostype.label("analyzer_ostype"),
            Analyzer.osversion.label("analyzer_osversion"),
            Node.location.label("node_location"),
            Node.category.label("node_category"),
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

    # Optimize count query by removing unnecessary joins and ORDER BY
    count_query = (
        db.query(Alert._ident)
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
    )

    # Apply filters to count query
    if severity:
        count_query = count_query.filter(Impact.severity == severity)
    if classification:
        count_query = count_query.filter(Classification.text.like(f"%{classification}%"))
    if start_date:
        count_query = count_query.filter(DetectTime.time >= start_date)
    if end_date:
        count_query = count_query.filter(DetectTime.time <= end_date)
    if source_ip:
        count_query = count_query.filter(func.binary(source_addr.address) == source_ip)
    if target_ip:
        count_query = count_query.filter(func.binary(target_addr.address) == target_ip)
    if analyzer_model:
        count_query = count_query.filter(Analyzer.model == analyzer_model)
    
    # Remove ORDER BY from count query and get total
    count_query = count_query.order_by(None)
    total = count_query.distinct().count()

    # Apply sorting to main query
    if sort_by == SortField.DETECT_TIME:
        sort_column = DetectTime.time
    elif sort_by == SortField.CREATE_TIME:
        sort_column = CreateTime.time
    elif sort_by == SortField.SEVERITY:
        sort_column = Impact.severity
    elif sort_by == SortField.CLASSIFICATION:
        sort_column = Classification.text
    elif sort_by == SortField.SOURCE_IP:
        sort_column = source_addr.address
    elif sort_by == SortField.TARGET_IP:
        sort_column = target_addr.address
    elif sort_by == SortField.ANALYZER:
        sort_column = Analyzer.name
    else:
        sort_column = Alert._ident

    if sort_order == SortOrder.ASC:
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Apply pagination
    offset = (page - 1) * size
    results = query.distinct().offset(offset).limit(size).all()

    # Convert results to response items
    items = []
    for result in results:
        node_info = None
        if result.analyzer_host or result.node_location or result.node_category:
            node_info = NodeInfo(
                name=result.analyzer_host,
                location=result.node_location,
                category=result.node_category,
            )

        analyzer_info = None
        if result.analyzer_name:
            analyzer_info = AnalyzerInfo(
                name=f"{result.analyzer_name} ({result.analyzer_host.split('.')[0]})" if result.analyzer_host else result.analyzer_name,
                node=node_info,
                model=result.analyzer_model,
                manufacturer=result.analyzer_manufacturer,
                version=result.analyzer_version,
                class_type=result.analyzer_class,
                ostype=result.analyzer_ostype,
                osversion=result.analyzer_osversion,
            )

        alert_item = AlertListItem(
            alert_id=str(result._ident),
            message_id=result.messageid,
            create_time=TimeInfo(
                time=result.create_time,
                usec=result.create_time_usec,
                gmtoff=result.create_time_gmtoff,
            )
            if result.create_time
            else None,
            detect_time=TimeInfo(
                time=result.detect_time,
                usec=result.detect_time_usec,
                gmtoff=result.detect_time_gmtoff,
            ),
            classification_text=result.classification_text,
            severity=result.severity,
            source_ipv4=result.source_ipv4,
            target_ipv4=result.target_ipv4,
            analyzer=analyzer_info,
        )
        items.append(alert_item)

    return AlertListResponse(
        total=total,
        items=items,
        page=page,
        size=size,
    )


@router.get("/groups", response_model=GroupedAlertResponse)
async def get_grouped_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Number of groups per page"),
    sort_by: SortField = Query(SortField.DETECT_TIME, description="Field to sort by"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order (asc/desc)"),
    severity: Optional[str] = None,
    classification: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    source_ip: Optional[str] = None,
    target_ip: Optional[str] = None,
    analyzer_model: Optional[str] = None,
    db: Session = Depends(get_prelude_db),
) -> GroupedAlertResponse:
    """
    Retrieve alerts grouped by source and target IP addresses.
    Each group includes detailed alert information with analyzers and times per classification.
    Supports pagination and filtering.
    """
    try:
        # Create aliases for source and target addresses
        source_addr = aliased(Address, name="source_addr")
        target_addr = aliased(Address, name="target_addr")

        # Base query for getting unique source-target pairs with total counts
        pairs_query = (
            db.query(
                source_addr.address.label("source_ipv4"),
                target_addr.address.label("target_ipv4"),
                func.count(Alert._ident).label("total_count"),
                func.max(DetectTime.time).label("latest_time"),
                func.max(Impact.severity).label("max_severity"),
                func.max(Classification.text).label("latest_classification"),
                func.max(Analyzer.name).label("analyzer_name"),
            )
            .select_from(Alert)
            .join(DetectTime, Alert._ident == DetectTime._message_ident)
            .outerjoin(Impact, Impact._message_ident == Alert._ident)
            .outerjoin(Classification, Classification._message_ident == Alert._ident)
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
            .group_by(
                source_addr.address,
                target_addr.address,
            )
        )

        # Apply filters
        if severity:
            pairs_query = pairs_query.filter(Impact.severity == severity)
        if classification:
            pairs_query = pairs_query.filter(Classification.text.like(f"%{classification}%"))
        if start_date:
            pairs_query = pairs_query.filter(DetectTime.time >= start_date)
        if end_date:
            pairs_query = pairs_query.filter(DetectTime.time <= end_date)
        if source_ip:
            pairs_query = pairs_query.filter(func.binary(source_addr.address) == source_ip)
        if target_ip:
            pairs_query = pairs_query.filter(func.binary(target_addr.address) == target_ip)
        if analyzer_model:
            pairs_query = pairs_query.filter(Analyzer.model == analyzer_model)

        # Apply sorting based on parameters
        if sort_by == SortField.DETECT_TIME:
            sort_column = func.max(DetectTime.time)
        elif sort_by == SortField.SEVERITY:
            sort_column = func.max(Impact.severity)
        elif sort_by == SortField.CLASSIFICATION:
            sort_column = func.max(Classification.text)
        elif sort_by == SortField.SOURCE_IP:
            sort_column = source_addr.address
        elif sort_by == SortField.TARGET_IP:
            sort_column = target_addr.address
        elif sort_by == SortField.ANALYZER:
            sort_column = func.max(Analyzer.name)
        else:
            sort_column = func.count(Alert._ident)  # Default sort by count

        if sort_order == SortOrder.ASC:
            pairs_query = pairs_query.order_by(sort_column.asc())
        else:
            pairs_query = pairs_query.order_by(sort_column.desc())

        # Get total count before pagination
        total_pairs = pairs_query.count()

        # Apply pagination to pairs query
        pairs_query = pairs_query.offset((page - 1) * size).limit(size)
        pairs = pairs_query.all()

        # Get detailed alert information for the paginated pairs
        alerts_query = (
            db.query(
                source_addr.address.label("source_ipv4"),
                target_addr.address.label("target_ipv4"),
                Classification.text.label("classification"),
                func.count(Alert._ident).label("count"),
                func.group_concat(distinct(Analyzer.name)).label("analyzers"),
                func.group_concat(distinct(Node.name)).label("analyzer_hosts"),
                func.max(DetectTime.time).label("latest_time"),
            )
            .select_from(Alert)
            .join(DetectTime, Alert._ident == DetectTime._message_ident)
            .outerjoin(Classification, Classification._message_ident == Alert._ident)
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
            .filter(
                tuple_(source_addr.address, target_addr.address).in_(
                    [(p.source_ipv4, p.target_ipv4) for p in pairs]
                )
            )
        )

        # Apply the same filters
        if severity:
            alerts_query = alerts_query.outerjoin(
                Impact, Impact._message_ident == Alert._ident
            ).filter(Impact.severity == severity)
        if classification:
            alerts_query = alerts_query.filter(Classification.text.like(f"%{classification}%"))
        if start_date:
            alerts_query = alerts_query.filter(DetectTime.time >= start_date)
        if end_date:
            alerts_query = alerts_query.filter(DetectTime.time <= end_date)
        if analyzer_model:
            alerts_query = alerts_query.filter(Analyzer.model == analyzer_model)

        # Group by source, target, and classification
        alerts_query = alerts_query.group_by(
            source_addr.address,
            target_addr.address,
            Classification.text,
        )

        alerts = alerts_query.all()

        # Build the response
        groups = []
        alerts_map = {}
        
        # Create a map of alerts for each source-target pair
        for a in alerts:
            key = (a.source_ipv4, a.target_ipv4)
            if key not in alerts_map:
                alerts_map[key] = []
            if a.classification:  # Only add if classification is not None
                # Process analyzer hosts to remove domain names
                analyzer_hosts = [
                    host.split('.')[0] if host else None 
                    for host in (a.analyzer_hosts.split(',') if a.analyzer_hosts else [])
                    if host
                ]
                analyzers = a.analyzers.split(',') if a.analyzers else []
                alerts_map[key].append(
                    GroupedAlertDetail(
                        classification=a.classification,
                        count=a.count,
                        analyzer=list(filter(None, analyzers)),
                        analyzer_host=analyzer_hosts,
                        time=a.latest_time,
                    )
                )

        # Build the final groups list
        for pair in pairs:
            key = (pair.source_ipv4, pair.target_ipv4)
            groups.append(
                GroupedAlert(
                    source_ipv4=pair.source_ipv4,
                    target_ipv4=pair.target_ipv4,
                    total_count=pair.total_count,
                    alerts=alerts_map.get(key, []),
                )
            )

        return GroupedAlertResponse(
            total=total_pairs,
            groups=groups,
            page=page,
            size=size,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching grouped alerts: {str(e)}",
        ) 


@router.get("/{alert_id}", response_model=AlertDetail)
async def get_alert_detail(
    alert_id: int,
    truncate_payload: bool = Query(False, description="Whether to truncate the payload data"),
    db: Session = Depends(get_prelude_db),
) -> AlertDetail:
    try:
        # Check if alert exists
        alert_exists = db.query(Alert._ident).filter(Alert._ident == alert_id).first()
        if not alert_exists:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Get base alert information
        alert = (
            db.query(Alert, CreateTime, DetectTime, Classification, Impact)
            .outerjoin(
                CreateTime,
                and_(
                    CreateTime._message_ident == Alert._ident,
                    CreateTime._parent_type == "A",
                ),
            )
            .outerjoin(DetectTime, DetectTime._message_ident == Alert._ident)
            .outerjoin(Classification, Classification._message_ident == Alert._ident)
            .outerjoin(Impact, Impact._message_ident == Alert._ident)
            .filter(Alert._ident == alert_id)
            .first()
        )

        # Get source information with complete address details
        source_info = (
            db.query(Source, Address)
            .outerjoin(
                Address,
                and_(
                    Address._message_ident == Source._message_ident,
                    Address._parent_type == "S",
                    Address._parent0_index == Source._index,
                ),
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
                    Address._parent_type == "T",
                    Address._parent0_index == Target._index,
                ),
            )
            .filter(Target._message_ident == alert_id)
            .first()
        )

        # Get analyzer information
        analyzer = (
            db.query(Analyzer, Node, Process)
            .outerjoin(
                Node,
                and_(
                    Node._message_ident == Analyzer._message_ident,
                    Node._parent_type == "A",
                    Node._parent0_index == Analyzer._index,
                ),
            )
            .outerjoin(
                Process,
                and_(
                    Process._message_ident == Analyzer._message_ident,
                    Process._parent_type == "A",
                    Process._parent0_index == Analyzer._index,
                ),
            )
            .filter(
                Analyzer._message_ident == alert_id,
                Analyzer._parent_type == "A",
                Analyzer._index == -1,
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
                AdditionalData._parent_type == "A",
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
            except Exception:  # Fixed bare except
                return value

        for row in add_data_rows:
            try:
                if row.type in ["integer", "real", "character"]:
                    additional_data[row.meaning] = clean_byte_string(str(row.data))
                elif row.type == "byte-string":
                    if row.meaning == "payload":
                        decoded = row.data.decode("utf-8", errors="ignore")
                        if truncate_payload and len(decoded) > 500:
                            decoded = decoded[:500] + "..."
                        additional_data[row.meaning] = decoded
                    else:
                        additional_data[row.meaning] = clean_byte_string(
                            row.data.decode("utf-8", errors="ignore")
                        )
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
                ip_version=next(
                    (int(d.data) for d in add_data_rows if d.meaning == "ip_ver"), None
                ),
                ip_hlen=next(
                    (int(d.data) for d in add_data_rows if d.meaning == "ip_hlen"), None
                ),
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
                ip_version=next(
                    (int(d.data) for d in add_data_rows if d.meaning == "ip_ver"), None
                ),
                ip_hlen=next(
                    (int(d.data) for d in add_data_rows if d.meaning == "ip_hlen"), None
                ),
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
                    name=analyzer[1].name,
                )

            process_info = None
            if analyzer[2]:
                process_info = ProcessInfo(
                    name=analyzer[2].name, pid=analyzer[2].pid, path=analyzer[2].path
                )

            analyzer_info = AnalyzerInfo(
                name=analyzer[0].name,
                node=node_info,
                model=analyzer[0].model,
                manufacturer=analyzer[0].manufacturer,
                version=analyzer[0].version,
                class_type=getattr(analyzer[0], "class", None),
                ostype=analyzer[0].ostype,
                osversion=analyzer[0].osversion,
                process=process_info,
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
            alert_id=str(alert[0]._ident),
            message_id=alert[0].messageid,
            create_time=TimeInfo(
                time=alert[1].time, usec=alert[1].usec, gmtoff=alert[1].gmtoff
            )
            if alert[1]
            else None,
            detect_time=TimeInfo(
                time=alert[2].time, usec=alert[2].usec, gmtoff=alert[2].gmtoff
            ),
            classification_text=alert[3].text if alert[3] else None,
            classification_ident=alert[3].ident if alert[3] else None,
            severity=alert[4].severity if alert[4] else None,
            description=alert[4].description if alert[4] else None,
            completion=alert[4].completion if alert[4] else None,
            impact_type=alert[4].type if alert[4] else None,
            source=source,
            target=target,
            analyzer=analyzer_info,
            references=[
                ReferenceInfo(
                    origin=ref.origin, name=ref.name, url=ref.url, meaning=ref.meaning
                )
                for ref in unique_refs
            ],
            services=[
                ServiceInfo(
                    port=svc.port,
                    protocol=svc.iana_protocol_name,
                    direction="source" if svc._parent_type == "S" else "target",
                )
                for svc in unique_services
            ],
            additional_data=additional_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing alert: {str(e)}") 