from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime
from enum import Enum
from app.database.config import (
    get_prelude_db,
    apply_standard_alert_filters,
    apply_sorting,
)
from app.database.query_builders import (
    build_alert_base_query,
    build_grouped_alerts_query,
    build_grouped_alerts_count_query,
    build_grouped_alerts_detail_query,
    build_alert_detail_query,
)
from app.database.models import (
    alert_result_to_list_item,
    grouped_alert_to_response,
    process_grouped_alerts_details,
    build_analyzer_info,
    build_node_info,
    build_process_info,
    process_additional_data,
)
from app.models.prelude import (
    Alert,
    Impact,
    Classification,
    DetectTime,
    Analyzer,
    CreateTime,
    ProcessArg,
    ProcessEnv,
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
    PaginatedResponse,
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
    TOTAL_COUNT = "total_count"  # For grouped alerts


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
    """Retrieve a paginated list of alerts with filtering and sorting."""
    # Future date validation prevents empty results from test queries
    if start_date:
        start_date_tz = ensure_timezone(start_date)
        if start_date_tz is not None and start_date_tz > get_current_time():
            return AlertListResponse(
                items=[],
                pagination=PaginatedResponse(total=0, page=page, size=size, pages=0),
            )

    query, models = build_alert_base_query(db)

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

    query = apply_sorting(query, sort_by, sort_order, sort_options, DetectTime.time)

    # SQLAlchemy 2.0 optimized count using scalar_subquery
    # This is more efficient than creating a full subquery
    count_stmt = select(func.count()).select_from(query.distinct().subquery())
    total = db.scalar(count_stmt) or 0

    total_pages = (total + size - 1) // size

    offset = (page - 1) * size

    # distinct() prevents duplicates from joins, _ident ensures stable pagination
    alerts = db.execute(
        query.distinct().order_by(Alert._ident).offset(offset).limit(size)
    ).all()

    alert_items = [alert_result_to_list_item(alert) for alert in alerts]

    return AlertListResponse(
        items=alert_items,
        pagination=PaginatedResponse(
            total=total, page=page, size=size, pages=total_pages
        ),
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
    """Retrieve alerts grouped by source and target IP addresses."""
    try:
        # Include optional joins only when needed for sorting or filtering
        need_cls = (classification is not None) or (sort_by == SortField.CLASSIFICATION)
        need_analyzer = (analyzer_model is not None) or (sort_by == SortField.ANALYZER)
        need_impact = (severity is not None) or (sort_by == SortField.SEVERITY)

        pairs_query, models = build_grouped_alerts_query(
            db,
            include_classification=need_cls,
            include_analyzer=need_analyzer,
            include_impact=need_impact,
        )
        count_query, count_models = build_grouped_alerts_count_query(
            db,
            include_classification=need_cls,
            include_analyzer=need_analyzer,
            include_impact=need_impact,
        )

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
            Analyzer=Analyzer,
        )

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
            Analyzer=Analyzer,
        )

        # Determine order-by columns for source/target depending on path
        source_order_col = (
            models["source_addr"].address if "source_addr" in models else models.get("source_ip_order_col")
        )
        target_order_col = (
            models["target_addr"].address if "target_addr" in models else models.get("target_ip_order_col")
        )

        count_expr = (
            func.count(func.distinct(DetectTime._message_ident))
            if need_cls
            else func.count()
        )

        sort_option = {
            "detect_time": func.max(DetectTime.time),
            "severity": func.max(Impact.severity),
            "classification": func.max(Classification.text),
            "source_ip": source_order_col,
            "target_ip": target_order_col,
            "analyzer": func.max(Analyzer.name),
            # Keep sort functions aligned with the aggregation strategy used in the builder
            "alert_id": count_expr,
            "total_count": count_expr,
        }

        order_by_clause = sort_option.get(sort_by.value)
        if order_by_clause is not None:
            if sort_order == SortOrder.DESC:
                order_by_clause = order_by_clause.desc()
            pairs_query = pairs_query.order_by(order_by_clause)

        total_pairs = db.scalar(count_query) or 0

        pairs_query = pairs_query.offset((page - 1) * size).limit(size)
        pairs = db.execute(pairs_query).all()

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
            Analyzer=Analyzer,
        )

        alerts = db.execute(alerts_query).all()

        alerts_map = process_grouped_alerts_details(alerts)

        groups = [grouped_alert_to_response(pair, alerts_map) for pair in pairs]

        # Calculate total number of alerts represented by the current page
        total_alerts_on_page = sum(group.total_count or 0 for group in groups)

        total_pages = (total_pairs + size - 1) // size

        return GroupedAlertResponse(
            groups=groups,
            pagination=PaginatedResponse(
                total=total_pairs, page=page, size=size, pages=total_pages
            ),
            total_alerts=total_alerts_on_page,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching grouped alerts: {str(e)}",
        )


@router.get("/{alert_id}", response_model=AlertDetail)
async def get_alert_detail(
    alert_id: int,
    db: Session = Depends(get_prelude_db),
) -> AlertDetail:
    """Get detailed information about a specific alert."""
    try:
        alert_exists = db.execute(
            select(Alert._ident).where(Alert._ident == alert_id)
        ).scalar_one_or_none()
        if not alert_exists:
            raise HTTPException(status_code=404, detail="Alert not found")

        queries = build_alert_detail_query(db, alert_id)

        alert = db.execute(queries["base"]).first()
        source_info = db.execute(queries["source_info"]).first()
        source_addresses = db.execute(queries["source_addresses"]).scalars().all()
        target_info = db.execute(queries["target_info"]).first()
        target_addresses = db.execute(queries["target_addresses"]).scalars().all()
        analyzers_query = db.execute(queries["analyzers"]).all()
        references = db.execute(queries["references"]).scalars().all()
        services = db.execute(queries["services"]).scalars().all()
        web_services = db.execute(queries["web_services"]).scalars().all()
        alert_idents = db.execute(queries["alert_idents"]).scalars().all()
        add_data_rows = db.execute(queries["additional_data"]).scalars().all()

        # Always return full, non-truncated data in multiple formats
        additional_data = process_additional_data(add_data_rows)

        analyzers_info = []
        for analyzer in analyzers_query:
            process_args = (
                db.execute(
                    select(ProcessArg.arg)
                    .where(
                        ProcessArg._message_ident == alert_id,
                        ProcessArg._parent_type == "A",
                        ProcessArg._parent0_index == analyzer[0]._index,
                    )
                    .order_by(ProcessArg._index)
                )
                .scalars()
                .all()
            )

            process_env = (
                db.execute(
                    select(ProcessEnv.env)
                    .where(
                        ProcessEnv._message_ident == alert_id,
                        ProcessEnv._parent_type == "A",
                        ProcessEnv._parent0_index == analyzer[0]._index,
                    )
                    .order_by(ProcessEnv._index)
                )
                .scalars()
                .all()
            )

            node_info = build_node_info(analyzer[1]) if analyzer[1] else None

            process_info = (
                build_process_info(analyzer[2], process_args, process_env)
                if analyzer[2]
                else None
            )

            analyzer_time_info = None
            if analyzer[3]:
                analyzer_time_info = AnalyzerTimeInfo(
                    timestamp=analyzer[3].time,
                    usec=analyzer[3].usec,
                    gmtoff=analyzer[3].gmtoff,
                )

            analyzer_info = build_analyzer_info(
                analyzer_data=analyzer[0],
                node_info=node_info,
                process_info=process_info,
                analyzer_time_info=analyzer_time_info,
            )
            analyzers_info.append(analyzer_info)

        source = None
        if source_info and source_info[1]:
            source_node = build_node_info(source_info[3]) if source_info[3] else None

            source_process = None
            if source_info[4]:
                source_process = ProcessInfo(
                    name=source_info[4].name,
                    pid=source_info[4].pid,
                    path=source_info[4].path,
                    args=[],
                    env=[],
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
                protocol_number=source_info[2].iana_protocol_number
                if source_info[2]
                else None,
                node=source_node,
                heartbeat_process=source_process,
                addresses=[addr[0] for addr in source_addresses],
            )

        target = None
        if target_info and target_info[1]:
            target_node = build_node_info(target_info[3]) if target_info[3] else None

            target_process = (
                build_process_info(
                    target_info[4],
                    [],
                    [],
                )
                if target_info[4]
                else None
            )

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
                protocol_number=target_info[2].iana_protocol_number
                if target_info[2]
                else None,
                node=target_node,
                heartbeat_process=target_process,
                addresses=[addr[0] for addr in target_addresses],
            )

        # Deduplicate services (parent_type distinguishes source vs target)
        seen_services = set()
        unique_services = []
        for svc in services:
            service_key = (svc.port, svc.iana_protocol_name, svc._parent_type)
            if service_key not in seen_services:
                seen_services.add(service_key)
                unique_services.append(svc)

        seen_refs = set()
        unique_refs = []
        for ref in references:
            ref_key = (ref.origin, ref.name, ref.url)
            if ref_key not in seen_refs:
                seen_refs.add(ref_key)
                unique_refs.append(ref)

        return AlertDetail(
            id=str(alert[0]._ident) if alert and alert[0] else "",
            message_id=alert[0].messageid if alert and alert[0] else "",
            created_at=TimeInfo(
                timestamp=alert[1].time, usec=alert[1].usec, gmtoff=alert[1].gmtoff
            )
            if alert and alert[1]
            else None,
            detected_at=TimeInfo(
                timestamp=alert[2].time if alert and alert[2] else get_current_time(),
                usec=alert[2].usec if alert and alert[2] else 0,
                gmtoff=alert[2].gmtoff if alert and alert[2] else 0,
            ),
            classification_text=alert[3].text if alert and alert[3] else None,
            classification_ident=alert[3].ident if alert and alert[3] else None,
            severity=alert[4].severity if alert and alert[4] else None,
            description=alert[4].description if alert and alert[4] else None,
            completion=alert[4].completion if alert and alert[4] else None,
            impact_type=alert[4].type if alert and alert[4] else None,
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


# DELETE endpoint removed - Prelude DB is read-only as per architecture design
# Alert data should only be modified through the Prelude IDS system itself
