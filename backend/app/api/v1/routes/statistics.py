from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import Alerts, get_current_user
from app.core.datetime_utils import get_current_time
from app.schemas.alerts import TimelineResponse
from app.schemas.filters import TimeFrame, TimelineParams

router = APIRouter(dependencies=[Depends(get_current_user, scope="function")])

# Window used when the request gives no start date.
DEFAULT_RANGES = {
    TimeFrame.MINUTE: timedelta(hours=1),
    TimeFrame.HOUR: timedelta(days=1),
    TimeFrame.DAY: timedelta(days=30),
    TimeFrame.WEEK: timedelta(days=90),
}


@router.get("/timeline")
async def get_timeline(
    repo: Alerts, params: Annotated[TimelineParams, Query()]
) -> TimelineResponse:
    """Alert counts per time bucket. Buckets without alerts are omitted."""
    end = params.end_date or get_current_time()
    start = params.start_date or end - DEFAULT_RANGES[params.time_frame]
    window = params.model_copy(update={"start_date": start, "end_date": end})
    return TimelineResponse(
        time_frame=params.time_frame.value,
        start_date=start,
        end_date=end,
        data=await repo.timeline(window, params.time_frame),
    )
