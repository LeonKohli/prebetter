from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from sqlalchemy.sql import distinct
from typing import Optional
from datetime import datetime
from enum import Enum
from app.database.config import get_prelude_db, apply_standard_alert_filters, apply_sorting
from app.database.query_builders import (
    build_alert_base_query,
    build_alert_count_query,
    build_grouped_alerts_query,
    build_grouped_alerts_detail_query,
    build_alert_detail_query
)
from app.database.models import (
    alert_result_to_list_item,
    grouped_alert_to_response,
    process_grouped_alerts_details,
    build_analyzer_info,
    build_node_info,
    build_process_info,
    process_additional_data
)
from app.models.prelude import (
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
    WebService,
    Alertident,
    ProcessArg,
    ProcessEnv,
    AnalyzerTime,
    Assessment,
)
from app.schemas.prelude import (
    AlertListResponse,
    AlertDetail,
    TimeInfo,
    NetworkInfo,
    ProcessInfo,
    ReferenceInfo,
    ServiceInfo,
    WebServiceInfo,
    AlertIdentInfo,
    AnalyzerTimeInfo,
    GroupedAlertResponse,
)
from app.core.datetime_utils import get_current_time, ensure_timezone
from app.api.v1.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

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
    """
    Retrieve a paginated list of alerts with filtering and sorting options.
    """
    # Validate date ranges and handle future dates
    # Required for tests: return empty result for future dates
    
    # Check for future date - if start_date is in the future, return empty result immediately
    if start_date and ensure_timezone(start_date) > get_current_time():
        return AlertListResponse(
            total=0,
            items=[],
            page=page,
            size=size
        )
    
    # Get base query and model aliases
    query, models = build_alert_base_query(db)
    
    # Apply filters
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
    
    # Get count query and apply the same filters
    count_query, count_models = build_alert_count_query(db)
    count_query = apply_standard_alert_filters(
        query=count_query,
        severity=severity,
        classification=classification,
        start_date=start_date,
        end_date=end_date,
        source_ip=source_ip,
        target_ip=target_ip,
        analyzer_model=analyzer_model,
        **count_models,
        Impact=Impact,
        Classification=Classification,
        DetectTime=DetectTime,
        Analyzer=Analyzer
    )
    
    # Apply sorting with support for multiple fields
    sort_options = {
        SortField.DETECT_TIME: DetectTime.time,
        SortField.CREATE_TIME: CreateTime.time,
        SortField.SEVERITY: Impact.severity,
        SortField.CLASSIFICATION: Classification.text,
        SortField.SOURCE_IP: models["source_addr"].address,
        SortField.TARGET_IP: models["target_addr"].address,
        SortField.ANALYZER: Analyzer.name,
        SortField.ALERT_ID: Alert._ident,
    }
    
    # Apply sorting to the main query
    query = apply_sorting(query, sort_by, sort_order, sort_options, DetectTime.time)
    
    # Calculate total distinct records with optimized query
    # Use a more optimized approach to avoid cartesian product warning
    
    # Create a new query just for counting alert IDs
    
    # We need to handle the count in a way that avoids cartesian products
    # Use a direct count of distinct Alert._ident that doesn't rely on joined tables
    alert_ids_query = db.query(distinct(Alert._ident))
    
    # Only add the joins that are needed for filtering
    if start_date or end_date:
        alert_ids_query = alert_ids_query.join(DetectTime, Alert._ident == DetectTime._message_ident)
    
    if severity:
        alert_ids_query = alert_ids_query.join(Impact, Impact._message_ident == Alert._ident)
    
    if classification:
        alert_ids_query = alert_ids_query.join(Classification, Classification._message_ident == Alert._ident)
    
    if analyzer_model:
        alert_ids_query = alert_ids_query.join(
            Analyzer, 
            and_(
                Analyzer._message_ident == Alert._ident,
                Analyzer._parent_type == "A",
                Analyzer._index == -1
            )
        )
    
    # Apply the same filters to this query
    alert_ids_query = apply_standard_alert_filters(
        query=alert_ids_query,
        severity=severity,
        classification=classification,
        start_date=start_date,
        end_date=end_date,
        source_ip=source_ip,
        target_ip=target_ip,
        analyzer_model=analyzer_model,
        Impact=Impact,
        Classification=Classification,
        DetectTime=DetectTime,
        Analyzer=Analyzer
    )
    
    # Count the distinct alert IDs
    total = alert_ids_query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    
    # Get paginated alerts with all necessary information
    alerts = query.distinct().order_by(Alert._ident).offset(offset).limit(size).all()
    
    # Convert to response schema
    alert_items = [alert_result_to_list_item(alert) for alert in alerts]

    return AlertListResponse(
        total=total,
        items=alert_items,
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
        # Get query for grouped alerts pairs
        pairs_query, models = build_grouped_alerts_query(db)
        
        # Apply filters
        pairs_query = apply_standard_alert_filters(
            query=pairs_query,
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

        # Prepare sort options for grouped alerts
        source_addr = models["source_addr"]
        target_addr = models["target_addr"]
        
        # Define sort options for grouped alerts
        sort_option = {
            "detect_time": func.max(DetectTime.time),
            "severity": func.max(Impact.severity),
            "classification": func.max(Classification.text),
            "source_ip": source_addr.address,
            "target_ip": target_addr.address,
            "analyzer": func.max(Analyzer.name),
            "alert_id": func.count(Alert._ident)  # Actually count in this context
        }
        
        # Apply the selected sort option
        order_by_clause = sort_option.get(sort_by.value)
        if order_by_clause is not None:
            if sort_order == SortOrder.DESC:
                order_by_clause = order_by_clause.desc()
            pairs_query = pairs_query.order_by(order_by_clause)

        # Get total count before pagination
        total_pairs = pairs_query.count()

        # Apply pagination to pairs query
        pairs_query = pairs_query.offset((page - 1) * size).limit(size)
        pairs = pairs_query.all()

        # Get detailed alert information for the paginated pairs
        alerts_query, alert_models = build_grouped_alerts_detail_query(db, pairs)
        
        # Apply the same filters
        alerts_query = apply_standard_alert_filters(
            query=alerts_query,
            severity=severity,
            classification=classification,
            start_date=start_date,
            end_date=end_date,
            source_ip=source_ip,
            target_ip=target_ip,
            analyzer_model=analyzer_model,
            **alert_models,
            Impact=Impact,
            Classification=Classification,
            DetectTime=DetectTime,
            Analyzer=Analyzer
        )

        # Group by source, target, and classification
        source_addr = alert_models["source_addr"]
        target_addr = alert_models["target_addr"]
        
        # Group by first, then apply limit
        alerts_query = alerts_query.group_by(
            source_addr.address,
            target_addr.address,
            Classification.text,
        )
        
        # Add a limit after group_by
        alerts_query = alerts_query.limit(1000)
        
        # Execute query
        alerts = alerts_query.all()

        # Process the alerts using the utility function
        alerts_map = process_grouped_alerts_details(alerts)
        
        # Build the final groups list using the utility function
        groups = [grouped_alert_to_response(pair, alerts_map) for pair in pairs]

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
    """
    Get detailed information about a specific alert including all related entities.
    """
    try:
        # Check if alert exists
        alert_exists = db.query(Alert._ident).filter(Alert._ident == alert_id).first()
        if not alert_exists:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Use the query builder to get all the queries we need
        queries = build_alert_detail_query(db, alert_id)
        
        # Execute the queries
        alert = queries["base"].first()
        source_info = queries["source_info"].first()
        source_addresses = queries["source_addresses"].all()
        target_info = queries["target_info"].first()
        target_addresses = queries["target_addresses"].all()
        analyzers_query = queries["analyzers"].all()
        references = queries["references"].all()
        services = queries["services"].all()
        web_services = queries["web_services"].all()
        alert_idents = queries["alert_idents"].all()
        add_data_rows = queries["additional_data"].all()

        # Process additional data using the utility function
        additional_data = process_additional_data(add_data_rows, truncate_payload)

        # Build list of analyzer info objects
        analyzers_info = []
        for analyzer in analyzers_query:
            # Get process arguments for this analyzer
            process_args = (
                db.query(ProcessArg.arg)
                .filter(
                    ProcessArg._message_ident == alert_id,
                    ProcessArg._parent_type == "A",
                    ProcessArg._parent0_index == analyzer[0]._index,
                )
                .order_by(ProcessArg._index)
                .all()
            )

            # Get process environment variables for this analyzer
            process_env = (
                db.query(ProcessEnv.env)
                .filter(
                    ProcessEnv._message_ident == alert_id,
                    ProcessEnv._parent_type == "A",
                    ProcessEnv._parent0_index == analyzer[0]._index,
                )
                .order_by(ProcessEnv._index)
                .all()
            )

            # Build node info using the utility function
            node_info = build_node_info(analyzer[1]) if analyzer[1] else None

            # Build process info using the utility function
            process_info = build_process_info(analyzer[2], process_args, process_env) if analyzer[2] else None

            # Build analyzer time info
            analyzer_time_info = None
            if analyzer[3]:  # If AnalyzerTime exists
                analyzer_time_info = AnalyzerTimeInfo(
                    time=analyzer[3].time,
                    usec=analyzer[3].usec,
                    gmtoff=analyzer[3].gmtoff,
                )

            # Build analyzer info using the utility function
            analyzer_info = build_analyzer_info(
                analyzer_data=analyzer[0],
                node_info=node_info,
                process_info=process_info,
                analyzer_time_info=analyzer_time_info
            )
            analyzers_info.append(analyzer_info)

        # Build source network info with complete details
        source = None
        if source_info and source_info[1]:  # Check if Address info exists
            # Build node info for source using the utility function
            source_node = build_node_info(source_info[3]) if source_info[3] else None

            # Build heartbeat process info
            source_process = None
            if source_info[4]:  # If Process exists
                source_process = ProcessInfo(
                    name=source_info[4].name,
                    pid=source_info[4].pid,
                    path=source_info[4].path,
                    args=[],  # Process args not relevant for heartbeat
                    env=[],   # Process env not relevant for heartbeat
                )

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
                protocol=source_info[2].iana_protocol_name if source_info[2] else None,
                protocol_number=source_info[2].iana_protocol_number if source_info[2] else None,
                node=source_node,
                heartbeat_process=source_process,
                addresses=[addr[0] for addr in source_addresses],
            )

        # Build target network info with complete details
        target = None
        if target_info and target_info[1]:  # Check if Address info exists
            # Build node info for target using the utility function
            target_node = build_node_info(target_info[3]) if target_info[3] else None

            # Build heartbeat process info using the utility function
            target_process = build_process_info(
                target_info[4], 
                [], # No args for heartbeat
                []  # No env for heartbeat
            ) if target_info[4] else None

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
                protocol=target_info[2].iana_protocol_name if target_info[2] else None,
                protocol_number=target_info[2].iana_protocol_number if target_info[2] else None,
                node=target_node,
                heartbeat_process=target_process,
                addresses=[addr[0] for addr in target_addresses],
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
            analyzers=analyzers_info,
            references=[
                ReferenceInfo(
                    origin=ref.origin, name=ref.name, url=ref.url, meaning=ref.meaning
                )
                for ref in unique_refs
            ],
            services=[
                ServiceInfo(
                    port=svc.port,
                    protocol=svc.protocol,
                    direction="source" if svc._parent_type == "S" else "target",
                    ip_version=svc.ip_version,
                    name=svc.name,
                    iana_protocol_number=svc.iana_protocol_number,
                    iana_protocol_name=svc.iana_protocol_name,
                    portlist=svc.portlist,
                    ident=svc.ident,
                )
                for svc in unique_services
            ],
            web_services=[
                WebServiceInfo(
                    url=ws.url,
                    cgi=ws.cgi,
                    http_method=ws.http_method,
                )
                for ws in web_services
            ],
            alert_idents=[
                AlertIdentInfo(
                    alertident=ai.alertident,
                    analyzerid=ai.analyzerid,
                )
                for ai in alert_idents
            ],
            additional_data=additional_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing alert: {str(e)}")

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    db: Session = Depends(get_prelude_db),
) -> dict:
    """
    Delete a specific alert and all its related data.
    """
    try:
        # Check if alert exists
        alert = db.query(Alert).filter(Alert._ident == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Delete related data in the correct order to maintain referential integrity
        # The order matters due to foreign key constraints
        related_tables = [
            ProcessArg,      # Process arguments
            ProcessEnv,      # Process environment variables
            Process,         # Process information
            Service,         # Service information
            WebService,      # Web service information
            Address,         # IP addresses
            Reference,       # References
            AdditionalData,  # Additional data
            Alertident,      # Alert identifiers
            AnalyzerTime,    # Analyzer timestamps
            Node,           # Node information
            Analyzer,        # Analyzer information
            Source,         # Source information
            Target,         # Target information
            Impact,         # Impact information
            Classification, # Classification information
            DetectTime,     # Detection time
            CreateTime,     # Creation time
            Assessment,     # Alert assessment
        ]

        # Delete all related records (these use _message_ident)
        for table in related_tables:
            db.query(table).filter(table._message_ident == alert_id).delete(synchronize_session=False)

        # Delete the alert itself (uses _ident)
        db.query(Alert).filter(Alert._ident == alert_id).delete(synchronize_session=False)

        # Commit the transaction
        db.commit()

        return {"message": f"Alert {alert_id} and all related data successfully deleted"}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting alert: {str(e)}")
