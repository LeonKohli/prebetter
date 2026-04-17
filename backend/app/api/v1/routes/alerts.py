"""
Alert routes using FastAPI best practices.

- Uses Repository pattern for data access
- Uses Pydantic filter schemas for consistent filtering
- Clean separation of concerns
"""

import asyncio
import logging
from enum import Enum
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database.config import (
    get_prelude_db,
    PreludeSessionLocal,
)
from app.database.query_builders import (
    build_alert_detail_query,
)
from app.repositories.alerts import (
    AlertRepository,
    GroupedAlertRepository,
    get_alert_repository,
    get_grouped_alert_repository,
)
from app.schemas.filters import AlertFilterParams, PaginationParams
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
)
from app.schemas.prelude import (
    AlertDeletionResponse,
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
from app.core.datetime_utils import get_current_time
from app.api.deps import (
    CurrentUser,
    get_current_user,
)

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user, scope="function")])


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


@router.get("", response_model=AlertListResponse)
@router.get("/", response_model=AlertListResponse)
def list_alerts(
    repo: Annotated[AlertRepository, Depends(get_alert_repository)],
    # Multiple Pydantic models as query params: use Depends() (NOT Query())
    # Query() is for ONE model capturing ALL params; Depends() allows MULTIPLE models
    filters: Annotated[AlertFilterParams, Depends()],
    pagination: Annotated[PaginationParams, Depends()],
    sort_by: Annotated[
        SortField, Query(description="Field to sort by")
    ] = SortField.DETECT_TIME,
    sort_order: Annotated[
        SortOrder, Query(description="Sort order (asc/desc)")
    ] = SortOrder.DESC,
) -> AlertListResponse:
    """Retrieve a paginated list of alerts with filtering and sorting."""

    # Repository injected via DI chain - no manual instantiation
    results, total = repo.get_list(
        filters=filters,
        pagination=pagination,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
    )

    # Convert results to response schema
    alert_items = [alert_result_to_list_item(alert) for alert in results]
    total_pages = pagination.total_pages(total)

    return AlertListResponse(
        items=alert_items,
        pagination=PaginatedResponse(
            total=total, page=pagination.page, size=pagination.size, pages=total_pages
        ),
    )


# SSE endpoint for real-time alert streaming
# IMPORTANT: Must be defined BEFORE /{alert_id} route to avoid path parameter matching
@router.get("/stream", response_class=EventSourceResponse)
async def stream_alerts(
    request: Request,
    last_id: Annotated[int | None, Query(description="Last known alert ID")] = None,
    require_ips: Annotated[
        bool,
        Query(description="Only notify for alerts with both source AND target IPs"),
    ] = True,
) -> AsyncIterable[ServerSentEvent]:
    """
    Server-Sent Events endpoint for real-time alert updates.

    Connect with EventSource and receive new alerts as they appear.
    Pass `last_id` to only receive alerts newer than that ID.

    IMPORTANT: This endpoint does NOT hold a database connection for the stream lifetime.
    Each poll acquires and releases a fresh session to avoid exhausting the pool.
    """

    current_last_id = last_id

    # Respect Last-Event-ID header for native SSE resume support
    header_last_id = request.headers.get("last-event-id")
    if header_last_id:
        try:
            parsed_header_id = int(header_last_id)
            current_last_id = max(parsed_header_id, current_last_id or 0)
        except ValueError:
            pass

    # Get initial max ID if not provided - use short-lived session
    if current_last_id is None:
        with PreludeSessionLocal() as db:
            max_id = db.scalar(select(func.max(Alert._ident)))
            current_last_id = max_id or 0

    # Send immediate comment to establish connection
    # This transitions EventSource from CONNECTING to OPEN instantly
    yield ServerSentEvent(comment="connected")

    while True:
        if await request.is_disconnected():
            break

        # Acquire fresh session for EACH poll - releases immediately after
        # This is critical: SSE connections can live for hours/days
        with PreludeSessionLocal() as db:
            repo = AlertRepository(db)
            query = repo.build_new_alerts_query(
                last_id=current_last_id,
                require_ips=require_ips,
            )
            results = db.execute(query).all()

            if results:
                # Send minimal notification - just alert count and latest ID
                # Frontend uses this to trigger targeted refetch, not display
                latest_id = int(results[-1][0])  # Alert._ident is first column
                yield ServerSentEvent(
                    data={"count": len(results), "latest_id": latest_id},
                    event="alerts",
                    id=str(latest_id),
                )
                current_last_id = latest_id

        # Session is now CLOSED - connection returned to pool
        await asyncio.sleep(5)


@router.get("/groups", response_model=GroupedAlertResponse)
def get_grouped_alerts(
    repo: Annotated[GroupedAlertRepository, Depends(get_grouped_alert_repository)],
    filters: Annotated[AlertFilterParams, Depends()],
    pagination: Annotated[PaginationParams, Depends()],
    sort_by: Annotated[
        SortField, Query(description="Field to sort by")
    ] = SortField.TOTAL_COUNT,
    sort_order: Annotated[SortOrder, Query(description="Sort order")] = SortOrder.DESC,
) -> GroupedAlertResponse:
    """Retrieve alerts grouped by source and target IP addresses."""
    try:
        result = repo.get_groups(
            filters=filters,
            pagination=pagination,
            sort_by=sort_by.value,
            sort_order=sort_order.value,
        )

        alerts_map = process_grouped_alerts_details(result["details"])
        groups = [
            grouped_alert_to_response(pair, alerts_map) for pair in result["pairs"]
        ]
        total_alerts_on_page = sum(group.total_count or 0 for group in groups)

        return GroupedAlertResponse(
            groups=groups,
            pagination=PaginatedResponse(
                total=result["total_pairs"],
                page=pagination.page,
                size=pagination.size,
                pages=result["total_pages"],
            ),
            total_alerts=total_alerts_on_page,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching grouped alerts: %s", e)
        raise HTTPException(status_code=500, detail="Error fetching grouped alerts")


@router.get("/{alert_id}", response_model=AlertDetail)
def get_alert_detail(
    alert_id: int,
    db: Annotated[Session, Depends(get_prelude_db)],
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

        # Eagerly load all process args and envs to avoid N+1 queries
        all_process_args = db.execute(queries["process_args"]).all()
        all_process_envs = db.execute(queries["process_envs"]).all()

        # Build lookup dictionaries for O(1) access by analyzer index
        process_args_by_analyzer = {}
        for parent_idx, arg, arg_idx in all_process_args:
            if parent_idx not in process_args_by_analyzer:
                process_args_by_analyzer[parent_idx] = []
            process_args_by_analyzer[parent_idx].append(arg)

        process_envs_by_analyzer = {}
        for parent_idx, env, env_idx in all_process_envs:
            if parent_idx not in process_envs_by_analyzer:
                process_envs_by_analyzer[parent_idx] = []
            process_envs_by_analyzer[parent_idx].append(env)

        # Always return full, non-truncated data in multiple formats
        additional_data = process_additional_data(add_data_rows)

        analyzers_info = []
        for analyzer in analyzers_query:
            # Use pre-loaded data from dictionaries instead of executing N queries
            process_args = process_args_by_analyzer.get(analyzer[0]._index, [])
            process_env = process_envs_by_analyzer.get(analyzer[0]._index, [])

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
                timestamp=alert[1].time,
            )
            if alert and alert[1]
            else None,
            detected_at=TimeInfo(
                timestamp=alert[2].time if alert and alert[2] else get_current_time(),
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
            correlation_description=alert[5].name if alert and alert[5] else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing alert %s: %s", alert_id, e)
        raise HTTPException(status_code=500, detail="Error processing alert")


# Alert Deletion Endpoint


@router.delete("", response_model=AlertDeletionResponse)
@router.delete("/", response_model=AlertDeletionResponse)
def delete_alerts(
    db: Annotated[Session, Depends(get_prelude_db)],
    current_user: CurrentUser,
    ids: Annotated[
        str | None, Query(description="Alert ID(s) - '123' or '1,2,3'")
    ] = None,
    source_ip: Annotated[str | None, Query(description="Filter by source IP")] = None,
    target_ip: Annotated[str | None, Query(description="Filter by target IP")] = None,
) -> AlertDeletionResponse:
    """
    Delete alerts by IDs or by IP pair filter.

    Examples:
    - DELETE /alerts?ids=123
    - DELETE /alerts?ids=1,2,3
    - DELETE /alerts?source_ip=192.168.1.1&target_ip=10.0.0.1
    """
    from app.services.alert_deletion import AlertDeletionService

    service = AlertDeletionService(db)

    # Delete by IP pair
    if source_ip and target_ip:
        result = service.delete_grouped_alerts(
            source_ip, target_ip, current_user.username
        )

    # Delete by IDs
    elif ids:
        try:
            alert_ids = [int(i.strip()) for i in ids.split(",") if i.strip()]
        except ValueError:
            raise HTTPException(
                status_code=422, detail="Invalid alert IDs: all IDs must be numeric"
            )

        if len(alert_ids) == 0:
            raise HTTPException(
                status_code=422, detail="No valid alert IDs provided after parsing"
            )

        if len(alert_ids) == 1:
            result = service.delete_single_alert(alert_ids[0], current_user.username)
        else:
            result = service.delete_bulk_alerts(alert_ids, current_user.username)

    else:
        raise HTTPException(
            status_code=422, detail="Provide either 'ids' or 'source_ip'+'target_ip'"
        )

    return AlertDeletionResponse(
        deleted=result.total_alerts_deleted,
        rows=result.total_rows_deleted,
    )
