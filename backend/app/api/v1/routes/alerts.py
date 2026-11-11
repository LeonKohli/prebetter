import asyncio
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.api.deps import Alerts, get_current_user
from app.opensearch.queries import MAX_RESULT_WINDOW
from app.schemas.alerts import (
    AlertDetail,
    AlertListResponse,
    GroupedAlertResponse,
    PaginatedResponse,
)
from app.schemas.filters import AlertListParams, GroupListParams

router = APIRouter(dependencies=[Depends(get_current_user, scope="function")])

POLL_INTERVAL_SECONDS = 5.0


@router.get("")
@router.get("/")
async def list_alerts(
    repo: Alerts, params: Annotated[AlertListParams, Query()]
) -> AlertListResponse:
    """Alerts, newest first by default. Only the first 10,000 results are reachable."""
    if params.page * params.size > MAX_RESULT_WINDOW:
        raise HTTPException(
            status_code=422,
            detail=f"Only the first {MAX_RESULT_WINDOW} results can be paged; "
            "narrow the filter or sort differently",
        )
    items, total = await repo.list_alerts(params)
    reachable_pages = MAX_RESULT_WINDOW // params.size
    return AlertListResponse(
        items=items,
        pagination=PaginatedResponse(
            total=total,
            page=params.page,
            size=params.size,
            pages=min(params.total_pages(total), reachable_pages),
        ),
    )


@router.get("/groups")
async def list_alert_groups(
    repo: Alerts, params: Annotated[GroupListParams, Query()]
) -> GroupedAlertResponse:
    """Alerts grouped by (source, target) address pair."""
    groups, total = await repo.group_alerts(params)
    return GroupedAlertResponse(
        groups=groups,
        pagination=PaginatedResponse(
            total=total,
            page=params.page,
            size=params.size,
            pages=params.total_pages(total),
        ),
        total_alerts=sum(g.total_count for g in groups),
    )


# Registered before /{alert_id}, which would otherwise match "stream".
@router.get("/stream", response_class=EventSourceResponse)
async def stream_alerts(
    request: Request, repo: Alerts
) -> AsyncGenerator[ServerSentEvent]:
    """
    Tells the UI when to refetch; it carries no alert data. Event `alerts` reports how
    many documents were added since the previous poll.

    The trigger is the document count of the whole index pattern, not a timestamp
    cursor: a count also sees alerts that arrive late with an old event time.
    """
    seen = await repo.count()
    yield ServerSentEvent(comment="connected")
    while not await request.is_disconnected():
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        count = await repo.count()
        # A lower count means retention deleted an index: only the baseline moves.
        if count > seen:
            yield ServerSentEvent(data={"count": count - seen}, event="alerts")
        seen = count


@router.get("/{alert_id}")
async def get_alert(
    repo: Alerts,
    alert_id: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
) -> AlertDetail:
    alert = await repo.get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert
